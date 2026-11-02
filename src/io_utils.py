"""Downloading and loading."""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

from . import config as C

TIMEOUT = 300


def download_faostat(key, force=False):
    """Download a FAOSTAT archive into data/raw. Skips if already there."""
    name = C.FAOSTAT_FILES[key]
    target = C.RAW / f"{name}.csv"

    if target.exists() and not force:
        print(f"cached   {target.name}  ({target.stat().st_size / 1e6:.1f} MB)")
        return target

    r = requests.get(C.FAOSTAT_BULK.format(name=name), timeout=TIMEOUT)
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(f"{name}.csv") as src, open(target, "wb") as out:
            out.write(src.read())

    print(f"saved    {target.name}  ({target.stat().st_size / 1e6:.1f} MB)")
    return target


def load_faostat(key):
    """Load a FAOSTAT file, downloading it first if needed."""
    df = pd.read_csv(download_faostat(key), encoding="utf-8", low_memory=False)

    # latin-1 reads these files without error but mangles accented names
    bad = [a for a in df["Area"].unique() if "Ã" in a or "Â" in a]
    if bad:
        raise ValueError(f"wrong encoding, names came through as {bad[:3]}")

    return df


def year_columns(df):
    """Y1990 but not Y1990F or Y1990N."""
    return [c for c in df.columns if c.startswith("Y") and c[1:].isdigit()]


def faostat_to_long(df, id_cols):
    """Turn the year columns into rows."""
    long = df.melt(id_vars=id_cols, value_vars=year_columns(df),
                   var_name="year", value_name="value")
    long["year"] = long["year"].str[1:].astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long.dropna(subset=["value"])


def fetch_wdi(indicator, start=1961, end=2024):
    """Fetch one World Bank indicator for every country."""
    url = (f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
           f"?format=json&per_page=20000&date={start}:{end}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()

    meta, rows = r.json()
    if meta["pages"] > 1:
        raise RuntimeError(f"{indicator} came back in {meta['pages']} pages, data is incomplete")

    out = pd.DataFrame([{"iso3": x["countryiso3code"],
                         "wb_country": x["country"]["value"],
                         "year": int(x["date"]),
                         "value": x["value"]} for x in rows])
    return out[out["iso3"] != ""].dropna(subset=["value"])


def real_country_codes():
    """Country codes only. The API mixes in World, Euro area and similar."""
    r = requests.get("https://api.worldbank.org/v2/country?format=json&per_page=400",
                     timeout=TIMEOUT)
    r.raise_for_status()
    _, rows = r.json()
    return {x["id"] for x in rows if x["region"]["value"] != "Aggregates"}


def wdi_panel(indicators=None, start=1961, end=2024):
    """Fetch several indicators into one country-year table."""
    indicators = indicators or C.WDI_INDICATORS
    real = real_country_codes()

    frames = []
    for code, name in indicators.items():
        df = fetch_wdi(code, start, end).rename(columns={"value": name})
        df = df[df["iso3"].isin(real)]
        print(f"  {name:<20} {len(df):>7,} rows")
        frames.append(df.set_index(["iso3", "year"])[[name]])

    return pd.concat(frames, axis=1).reset_index()
