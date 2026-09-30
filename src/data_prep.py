"""
Project 1, Nigeria Yield Gap & Fertiliser Productivity
Step 1: Data collection and cleaning.

Sources (all open, no authentication required):
  * FAOSTAT bulk download  : Production_Crops_Livestock_E_Africa.zip  (yield, area harvested, production)
  * FAOSTAT bulk download  : Inputs_FertilizersNutrient_E_Africa.zip  (N, P2O5, K2O nutrient use)
  * FAOSTAT bulk download  : Prices_E_Africa.zip                      (producer prices, USD/tonne)
  * World Bank WDI API     : cereal yield, fertiliser kg/ha, arable land, population, etc.

Output: data/processed/*.csv  (tidy, analysis-ready)

Run:  python src/data_prep.py
"""
from __future__ import annotations
import io, zipfile, pathlib, sys
import pandas as pd
import numpy as np
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

FAO_BULK = "https://bulks-faostat.fao.org/production/{name}.zip"

# Crops that matter for Nigerian food security / smallholder livelihoods
FOCUS_CROPS = {
    "Maize (corn)": "Maize",
    "Rice": "Rice",
    "Cassava, fresh": "Cassava",
    "Sorghum": "Sorghum",
    "Millet": "Millet",
    "Yams": "Yam",
    "Cow peas, dry": "Cowpea",
    "Groundnuts, excluding shelled": "Groundnut",
}

# Comparator countries: African peers + global benchmarks for yield-gap framing
PEERS = ["Nigeria", "Ghana", "Ethiopia", "Egypt", "South Africa", "Kenya",
         "United Republic of Tanzania", "Uganda", "Mali", "Burkina Faso",
         "Côte d'Ivoire", "Cameroon", "Senegal", "Niger", "Benin"]

WDI_INDICATORS = {
    "AG.YLD.CREL.KG": "cereal_yield_kg_ha",
    "AG.CON.FERT.ZS": "fertilizer_kg_per_ha_arable",
    "AG.LND.ARBL.HA": "arable_land_ha",
    "AG.LND.CREL.HA": "cereal_area_ha",
    "NV.AGR.TOTL.ZS": "agri_valueadd_pct_gdp",
    "SP.RUR.TOTL.ZS": "rural_pop_pct",
    "SP.POP.TOTL":    "population",
    "AG.PRD.FOOD.XD": "food_production_index",
    "SN.ITK.DEFC.ZS": "undernourish_pct",
}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def download_fao(name: str) -> pathlib.Path:
    """Download and extract one FAOSTAT bulk archive; return the main CSV path."""
    target = RAW / f"{name}.csv"
    if target.exists():
        print(f"  [cache] {target.name}")
        return target
    url = FAO_BULK.format(name=name)
    print(f"  downloading {url}")
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        member = f"{name}.csv"
        with z.open(member) as f, open(target, "wb") as out:
            out.write(f.read())
    return target


def fao_wide_to_long(df: pd.DataFrame, value_name: str = "value") -> pd.DataFrame:
    """
    FAOSTAT bulk files are WIDE: one column per year (Y1961, Y1961F flag, Y1961N note).
    Melt to tidy long format and drop the flag/note columns.
    """
    year_cols = [c for c in df.columns
                 if c.startswith("Y") and c[1:].isdigit()]        # Y1961 but not Y1961F/N
    id_cols = [c for c in ["Area", "Item", "Element", "Unit"] if c in df.columns]
    long = df.melt(id_vars=id_cols, value_vars=year_cols,
                   var_name="year", value_name=value_name)
    long["year"] = long["year"].str[1:].astype(int)
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce")
    return long.dropna(subset=[value_name])


def fetch_wdi() -> pd.DataFrame:
    """Pull World Bank WDI indicators for all countries, 1961-2024."""
    out = RAW / "wdi_raw.csv"
    if out.exists():
        print("  [cache] wdi_raw.csv")
        return pd.read_csv(out)
    frames = []
    for code, name in WDI_INDICATORS.items():
        url = (f"https://api.worldbank.org/v2/country/all/indicator/{code}"
               f"?format=json&per_page=20000&date=1961:2024")
        j = requests.get(url, timeout=120).json()
        rows = j[1] or []
        for p in range(2, j[0]["pages"] + 1):
            rows += requests.get(url + f"&page={p}", timeout=120).json()[1] or []
        df = pd.DataFrame([{"iso3": x["countryiso3code"],
                            "country": x["country"]["value"],
                            "year": int(x["date"]),
                            name: x["value"]} for x in rows])
        frames.append(df.set_index(["iso3", "country", "year"]))
        print(f"  WDI {name}: {df.shape[0]} rows")
    wdi = pd.concat(frames, axis=1).reset_index()
    wdi = wdi[wdi["iso3"].str.len() == 3]          # drop aggregates with blank iso3
    wdi.to_csv(out, index=False)
    return wdi


# ----------------------------------------------------------------------------
# main build
# ----------------------------------------------------------------------------
def build_crop_panel() -> pd.DataFrame:
    """Tidy crop-level panel: area harvested, production, yield by country-crop-year."""
    path = download_fao("Production_Crops_Livestock_E_Africa")
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)

    df = df[df["Item"].isin(FOCUS_CROPS.keys()) & df["Area"].isin(PEERS)]
    df = df[df["Element"].isin(["Area harvested", "Production", "Yield"])]

    long = fao_wide_to_long(df)
    long["crop"] = long["Item"].map(FOCUS_CROPS)

    panel = (long.pivot_table(index=["Area", "crop", "year"],
                              columns="Element", values="value", aggfunc="first")
                 .reset_index()
                 .rename(columns={"Area": "country",
                                  "Area harvested": "area_ha",
                                  "Production": "production_t",
                                  "Yield": "yield_raw"}))

    # FAOSTAT yield unit is kg/ha in current releases; recompute defensively so the
    # unit is unambiguous and internally consistent with production / area.
    panel["yield_t_ha"] = panel["production_t"] / panel["area_ha"]
    panel = panel[(panel["area_ha"] > 0) & (panel["production_t"] > 0)]
    panel = panel[panel["yield_t_ha"].between(0.05, 100)]     # drop impossible values
    return panel.sort_values(["country", "crop", "year"]).reset_index(drop=True)


def build_fertiliser_panel() -> pd.DataFrame:
    """Total nutrient use (N + P2O5 + K2O, tonnes) per country-year, from FAOSTAT."""
    path = download_fao("Inputs_FertilizersNutrient_E_Africa")
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    df = df[df["Area"].isin(PEERS)]
    df = df[df["Element"].str.contains("Agricultural Use", case=False, na=False)]
    long = fao_wide_to_long(df)
    tot = (long.groupby(["Area", "year"])["value"].sum()
               .reset_index()
               .rename(columns={"Area": "country", "value": "nutrient_t"}))
    return tot


def build_price_panel() -> pd.DataFrame:
    """Annual producer prices (USD/tonne) per country-crop-year, from FAOSTAT."""
    path = download_fao("Prices_E_Africa")
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    df = df[df["Item"].isin(FOCUS_CROPS.keys()) & df["Area"].isin(PEERS)]
    df = df[df["Element"] == "Producer Price (USD/tonne)"]
    if "Months" in df.columns:
        df = df[df["Months"] == "Annual value"]
    long = fao_wide_to_long(df, value_name="producer_price_usd_t")
    long["crop"] = long["Item"].map(FOCUS_CROPS)
    return (long.groupby(["Area", "crop", "year"])["producer_price_usd_t"].mean()
                .reset_index().rename(columns={"Area": "country"}))


def main() -> None:
    print("STEP 1/4  crop production panel (FAOSTAT)")
    crops = build_crop_panel()
    print(f"          -> {len(crops):,} country-crop-year rows, "
          f"{crops.country.nunique()} countries, {crops.crop.nunique()} crops")

    print("STEP 2/4  fertiliser nutrient panel (FAOSTAT)")
    fert = build_fertiliser_panel()
    print(f"          -> {len(fert):,} country-year rows")

    print("STEP 3/4  producer prices (FAOSTAT)")
    prices = build_price_panel()
    print(f"          -> {len(prices):,} rows")

    print("STEP 4/4  macro & input context (World Bank WDI)")
    wdi = fetch_wdi()
    print(f"          -> {len(wdi):,} country-year rows")

    # ---- merge into the two analysis tables -------------------------------
    crops = crops.merge(prices, on=["country", "crop", "year"], how="left")
    crops["output_value_usd"] = crops["production_t"] * crops["producer_price_usd_t"]

    macro = (wdi.merge(fert, on=["country", "year"], how="left"))
    macro["nutrient_kg_per_ha"] = (macro["nutrient_t"] * 1000) / macro["arable_land_ha"]
    # Prefer FAOSTAT-derived intensity, fall back to the WDI series where missing
    macro["fert_kg_ha"] = macro["nutrient_kg_per_ha"].fillna(
        macro["fertilizer_kg_per_ha_arable"])

    crops.to_csv(PROC / "crop_panel.csv", index=False)
    macro.to_csv(PROC / "macro_panel.csv", index=False)

    ng = crops[crops.country == "Nigeria"]
    ng.to_csv(PROC / "nigeria_crop_panel.csv", index=False)

    print("\nSaved:")
    for f in ["crop_panel.csv", "macro_panel.csv", "nigeria_crop_panel.csv"]:
        print(f"  data/processed/{f}")
    print(f"\nNigeria coverage: {ng.year.min()}-{ng.year.max()}, "
          f"{ng.crop.nunique()} crops, {len(ng):,} rows")


if __name__ == "__main__":
    main()
