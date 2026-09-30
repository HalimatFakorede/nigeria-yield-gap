"""
Project 1, Step 2: Exploratory analysis, growth decomposition and yield-gap benchmarking.

Three questions:
  Q1. Has Nigerian crop output grown because farmers farm BETTER (yield) or just MORE land (area)?
  Q2. How large is Nigeria's yield gap against comparable peers, crop by crop?
  Q3. What is closing that gap worth, in tonnes and dollars?

METHODOLOGICAL NOTES (these matter, and they are the things an interviewer will probe)
  1. Peer benchmarking excludes Egypt and South Africa from the headline comparison.
     Egyptian agriculture is ~100% irrigated with >500 kg/ha fertiliser use; comparing
     rainfed Nigerian smallholders to it is not a like-for-like benchmark. Egypt is
     reported separately as the "technical frontier".
  2. A country only qualifies as a peer benchmark for a crop if it harvests at least
     MIN_AREA_HA of that crop. Without this filter, Niger appears as the "best cassava
     producer in Africa" off a trivial planted area, a classic small-denominator artefact.
  3. The aggregate decomposition uses Tornqvist (production-share weighted) index
     weights, not an unweighted average across crops, so cassava is not treated as
     equal in importance to cowpea.
  4. Start/end values are 3-year averages to strip out single-season weather noise.

Outputs: outputs/figures/*.png, outputs/tables/*.csv, outputs/results.json
Run:  python src/analysis.py
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"
for d in (FIG, TAB):
    d.mkdir(parents=True, exist_ok=True)

GREEN, GOLD, CLAY, INK, GREY = "#1f6b45", "#c8892c", "#a8543a", "#0d1b14", "#8a958e"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 160, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": .25, "grid.linestyle": "--",
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlepad": 12,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

# --- analysis parameters (single source of truth) ---------------------------
START, END = 1990, 2023
REF = (2019, 2023)              # "current" window for yield-gap benchmarking
MIN_AREA_HA = 100_000           # minimum harvested area to qualify as a peer benchmark
IRRIGATED_OUTLIERS = ["Egypt", "South Africa"]   # excluded from rainfed peer group

RESULTS: dict = {}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print(f"  figure -> outputs/figures/{name}")


# ============================================================================
# Q1. GROWTH DECOMPOSITION
# ============================================================================
def decompose_growth(crops, country="Nigeria", start=START, end=END):
    """
    Production P = Area A x Yield Y  ->  ln P = ln A + ln Y
    Total log growth splits exactly into an AREA component and a YIELD component.
    """
    d = crops[(crops.country == country) & crops.year.between(start, end)]
    rows = []
    for crop, g in d.groupby("crop"):
        g = g.sort_values("year")
        a0, a1 = g.head(3).area_ha.mean(), g.tail(3).area_ha.mean()
        y0, y1 = g.head(3).yield_t_ha.mean(), g.tail(3).yield_t_ha.mean()
        p0, p1 = g.head(3).production_t.mean(), g.tail(3).production_t.mean()
        rows.append({
            "crop": crop,
            "production_start_t": p0, "production_end_t": p1,
            "production_growth_pct": (p1 / p0 - 1) * 100,
            "area_growth_pct": (a1 / a0 - 1) * 100,
            "yield_growth_pct": (y1 / y0 - 1) * 100,
            "dlnA": np.log(a1 / a0), "dlnY": np.log(y1 / y0),
            "dlnP": np.log(p1 / p0),
        })
    dec = pd.DataFrame(rows)
    # Tornqvist weights: average production share across the two endpoints
    w0 = dec.production_start_t / dec.production_start_t.sum()
    w1 = dec.production_end_t / dec.production_end_t.sum()
    dec["weight"] = (w0 + w1) / 2
    return dec.sort_values("production_end_t", ascending=False).reset_index(drop=True)


def aggregate_shares(dec):
    """Production-weighted split of total output growth into area vs yield."""
    area_c = (dec.weight * dec.dlnA).sum()
    yield_c = (dec.weight * dec.dlnY).sum()
    total = area_c + yield_c
    return {
        "area_contribution_dln": area_c,
        "yield_contribution_dln": yield_c,
        "total_dln": total,
        "share_from_area_pct": area_c / total * 100,
        "share_from_yield_pct": yield_c / total * 100,
        "implied_total_growth_pct": (np.exp(total) - 1) * 100,
    }


def fig_decomposition(dec, agg):
    """
    Diverging bars: area and yield contributions can each be positive OR negative,
    so a stacked bar would be misleading. Grouped bars around zero are honest.
    """
    d = dec.sort_values("dlnP", ascending=True)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.0),
                             gridspec_kw={"width_ratios": [1.55, 1]})

    ax = axes[0]
    y = np.arange(len(d)); h = .38
    ax.barh(y + h / 2, d.area_growth_pct, height=h, color=CLAY,
            label="Area harvested (more land)")
    ax.barh(y - h / 2, d.yield_growth_pct, height=h, color=GREEN,
            label="Yield (better productivity)")
    ax.axvline(0, color=INK, lw=1.2)
    ax.set_yticks(y); ax.set_yticklabels(d.crop)
    ax.set_xlabel(f"Change {START}, {END} (%)")
    ax.set_title("Crop by crop: land grew, yields mostly did not", loc="left")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    for i, r in enumerate(d.itertuples()):
        ax.text(r.area_growth_pct + (9 if r.area_growth_pct >= 0 else -9), i + h / 2,
                f"{r.area_growth_pct:+.0f}%", va="center",
                ha="left" if r.area_growth_pct >= 0 else "right", fontsize=8, color=CLAY)
        ax.text(r.yield_growth_pct + (9 if r.yield_growth_pct >= 0 else -9), i - h / 2,
                f"{r.yield_growth_pct:+.0f}%", va="center",
                ha="left" if r.yield_growth_pct >= 0 else "right", fontsize=8, color=GREEN)
    ax.set_xlim(min(-80, d.yield_growth_pct.min() * 1.35), d.area_growth_pct.max() * 1.30)

    ax = axes[1]
    sa, sy = agg["share_from_area_pct"], agg["share_from_yield_pct"]
    ax.bar([0], [sa], color=CLAY, width=.55)
    ax.bar([1], [sy], color=GREEN, width=.55)
    ax.axhline(0, color=INK, lw=1.2)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Area\nexpansion", "Yield\ngrowth"])
    ax.set_ylabel("Share of total output growth (%)")
    ax.set_title("Weighted aggregate", loc="left")
    for x, v in [(0, sa), (1, sy)]:
        ax.text(x, v + (3 if v >= 0 else -6), f"{v:.0f}%", ha="center",
                fontsize=13, weight="bold", color=INK)
    ax.set_ylim(min(-20, sy * 1.5), max(120, sa * 1.2))

    fig.suptitle("Nigeria grew its food output by clearing more land, not by farming better",
                 x=.012, ha="left", fontsize=14, weight="bold")
    save(fig, "01_growth_decomposition.png")


# ============================================================================
# Q2. YIELD GAP
# ============================================================================
def yield_gap(crops, ref_years=REF, min_area=MIN_AREA_HA):
    d = crops[crops.year.between(*ref_years)]
    agg = (d.groupby(["crop", "country"])
             .agg(yield_t_ha=("yield_t_ha", "mean"), area_ha=("area_ha", "mean"))
             .reset_index())

    # Filter 1: a country must actually grow the crop at scale to be a benchmark
    credible = agg[agg.area_ha >= min_area]
    # Filter 2: rainfed peer group excludes irrigated outliers
    rainfed = credible[~credible.country.isin(IRRIGATED_OUTLIERS)]

    ng = agg[agg.country == "Nigeria"].set_index("crop")["yield_t_ha"]
    peers = rainfed[rainfed.country != "Nigeria"]
    best = peers.sort_values("yield_t_ha", ascending=False).groupby("crop").first()
    frontier = (credible[credible.country.isin(IRRIGATED_OUTLIERS)]
                .sort_values("yield_t_ha", ascending=False).groupby("crop").first())

    out = pd.DataFrame({
        "nigeria_t_ha": ng,
        "best_peer": best["country"],
        "best_peer_t_ha": best["yield_t_ha"],
        "best_peer_area_ha": best["area_ha"],
        "peer_median_t_ha": peers.groupby("crop")["yield_t_ha"].median(),
        "n_peers": peers.groupby("crop")["country"].nunique(),
        "frontier_country": frontier["country"],
        "frontier_t_ha": frontier["yield_t_ha"],
    }).dropna(subset=["nigeria_t_ha", "best_peer_t_ha"])

    out["gap_vs_best_pct"] = (out.best_peer_t_ha / out.nigeria_t_ha - 1) * 100
    out["gap_vs_median_pct"] = (out.peer_median_t_ha / out.nigeria_t_ha - 1) * 100
    out["nigeria_area_ha"] = agg[agg.country == "Nigeria"].set_index("crop")["area_ha"]
    return out.sort_values("gap_vs_best_pct", ascending=False)


def fig_yield_gap(gap, ref_years=REF):
    d = gap.sort_values("nigeria_t_ha")
    fig, ax = plt.subplots(figsize=(9.0, 4.9))
    y = np.arange(len(d))
    ax.hlines(y, d.nigeria_t_ha, d.best_peer_t_ha, color=GREY, lw=2.2, zorder=1)
    ax.scatter(d.nigeria_t_ha, y, s=105, color=GREEN, zorder=3, label="Nigeria")
    ax.scatter(d.peer_median_t_ha, y, s=60, color=GOLD, zorder=3,
               marker="D", label="Rainfed peer median")
    ax.scatter(d.best_peer_t_ha, y, s=105, color=CLAY, zorder=3, label="Best rainfed peer")
    for i, r in enumerate(d.itertuples()):
        ax.text(r.best_peer_t_ha + .35, i, f"{r.best_peer}  (+{r.gap_vs_best_pct:.0f}%)",
                va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(d.index)
    ax.set_xlabel("Average yield, tonnes per hectare")
    ax.set_xlim(0, d.best_peer_t_ha.max() * 1.42)
    ax.set_title(f"Nigeria's yield gap by crop, {ref_years[0]}, {ref_years[1]} average\n"
                 f"Rainfed African peers only, minimum {MIN_AREA_HA:,.0f} ha harvested",
                 loc="left")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    save(fig, "02_yield_gap.png")


# ============================================================================
# Q3. INPUT CONTEXT
# ============================================================================
def fig_fertiliser(macro):
    peers = ["Nigeria", "Ghana", "Ethiopia", "Kenya", "Egypt, Arab Rep.", "South Africa"]
    d = macro[macro.country.isin(peers) & macro.year.between(2000, 2022)]
    latest = (d.dropna(subset=["fert_kg_ha"]).sort_values("year")
                .groupby("country").tail(1).set_index("country")["fert_kg_ha"])

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.4))
    ax = axes[0]
    for c, g in d.dropna(subset=["fert_kg_ha"]).groupby("country"):
        col = GREEN if c == "Nigeria" else GREY
        ax.plot(g.year, g.fert_kg_ha, color=col, lw=2.7 if c == "Nigeria" else 1.2,
                alpha=1 if c == "Nigeria" else .75)
        ax.text(g.year.iloc[-1] + .3, g.fert_kg_ha.iloc[-1],
                f"{c} ({g.fert_kg_ha.iloc[-1]:.0f})", fontsize=7.5, color=col, va="center")
    ax.set_yscale("log")
    ax.set_title("Fertiliser intensity (log scale), 2000-2022", loc="left")
    ax.set_ylabel("kg nutrient per ha arable")
    ax.set_xlim(2000, 2031)

    ax = axes[1]
    dd = macro[macro.country.isin(["Nigeria", "Ghana", "Ethiopia", "Kenya"])
               & macro.year.between(1990, 2022)].dropna(subset=["cereal_yield_kg_ha"])
    for c, g in dd.groupby("country"):
        col = GREEN if c == "Nigeria" else GREY
        ax.plot(g.year, g.cereal_yield_kg_ha / 1000, color=col,
                lw=2.7 if c == "Nigeria" else 1.2)
        ax.text(g.year.iloc[-1] + .3, g.cereal_yield_kg_ha.iloc[-1] / 1000, c,
                fontsize=7.5, color=col, va="center")
    ax.set_title("Cereal yield, 1990-2022", loc="left")
    ax.set_ylabel("tonnes per hectare")
    ax.set_xlim(1990, 2030)
    fig.suptitle("Nigeria applies the least fertiliser of its peer group, and its cereal yields show it",
                 x=.012, ha="left", fontsize=13.5, weight="bold")
    save(fig, "03_fertiliser_and_yield.png")
    return latest.to_dict()


def fig_per_capita(crops, macro):
    ng = crops[crops.country == "Nigeria"].groupby("year")["production_t"].sum()
    pop = macro[macro.country == "Nigeria"].set_index("year")["population"]
    d = pd.DataFrame({"prod_t": ng, "pop": pop}).dropna()
    d = d[d.index.to_series().between(1990, 2024)]
    d["kg_per_person"] = d.prod_t * 1000 / d["pop"]
    idx = d / d.iloc[0] * 100
    peak_y = int(d.kg_per_person.idxmax())
    peak_v = float(d.kg_per_person.max())
    last_y, last_v = int(d.index[-1]), float(d.kg_per_person.iloc[-1])
    decline = (last_v / peak_v - 1) * 100

    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    ax.plot(idx.index, idx.prod_t, color=GREEN, lw=2.5, label="Food crop production")
    ax.plot(idx.index, idx["pop"], color=CLAY, lw=2.5, label="Population")
    ax.plot(idx.index, idx.kg_per_person, color=GOLD, lw=2.5, ls="--",
            label="Production per person")
    ax.axhline(100, color=GREY, lw=1)
    ax.axvline(peak_y, color=GOLD, lw=1, ls=":")
    ax.annotate(f"per-person output peaks {peak_y}\n({peak_v:.0f} kg), then falls {abs(decline):.0f}%",
                xy=(peak_y, idx.kg_per_person.loc[peak_y]),
                xytext=(peak_y - 13, idx.kg_per_person.max() * 1.02),
                fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="->", color=GREY, lw=1))
    ax.set_ylabel("Index, 1990 = 100")
    ax.set_title("Nigeria's food output per person peaked in 2006 and has fallen since\n"
                 "Eight major food crops", loc="left")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "04_production_per_capita.png")
    return {"kg_per_person_1990": float(d.kg_per_person.iloc[0]),
            "kg_per_person_latest": last_v, "latest_year": last_y,
            "peak_kg_per_person": peak_v, "peak_year": peak_y,
            "decline_from_peak_pct": decline}


# ============================================================================
def value_of_gap(crops, gap):
    """
    Tonnes and USD unlocked if Nigeria reached the rainfed peer MEDIAN yield
    on its existing harvested area. Producer prices: Nigeria's own FAOSTAT
    producer price where available, else the peer-group median for that crop.
    """
    ref = crops[crops.year.between(*REF)]
    ng = ref[ref.country == "Nigeria"]
    peer_price = ref.groupby("crop")["producer_price_usd_t"].median()

    rows = []
    for crop, g in ng.groupby("crop"):
        if crop not in gap.index:
            continue
        area = g.area_ha.mean()
        gain_t_ha = gap.loc[crop, "peer_median_t_ha"] - gap.loc[crop, "nigeria_t_ha"]
        if gain_t_ha <= 0:
            continue
        price = g.producer_price_usd_t.mean()
        src = "Nigeria (FAOSTAT)"
        if pd.isna(price):
            price, src = peer_price.get(crop, np.nan), "peer median (imputed)"
        extra_t = area * gain_t_ha
        rows.append({"crop": crop, "nigeria_area_ha": area,
                     "yield_gain_t_ha": gain_t_ha, "extra_tonnes": extra_t,
                     "price_usd_t": price, "price_source": src,
                     "value_usd": extra_t * price if pd.notna(price) else np.nan})
    v = pd.DataFrame(rows).sort_values("extra_tonnes", ascending=False)
    return v


def main():
    crops = pd.read_csv(PROC / "crop_panel.csv")
    macro = pd.read_csv(PROC / "macro_panel.csv")

    print("Q1  growth decomposition")
    dec = decompose_growth(crops)
    agg = aggregate_shares(dec)
    dec.to_csv(TAB / "growth_decomposition.csv", index=False)
    fig_decomposition(dec, agg)
    RESULTS["decomposition"] = {
        "period": f"{START}-{END}",
        "method": "Tornqvist production-share weighted log decomposition, 3-yr endpoint averages",
        **{k: round(v, 2) for k, v in agg.items()},
        "by_crop": dec.set_index("crop")[["production_growth_pct", "area_growth_pct",
                                          "yield_growth_pct", "weight"]].round(2).to_dict("index"),
    }
    print(dec[["crop", "production_growth_pct", "area_growth_pct",
               "yield_growth_pct", "weight"]].round(2).to_string(index=False))
    print(f"  AGGREGATE: {agg['share_from_area_pct']:.0f}% of growth from area, "
          f"{agg['share_from_yield_pct']:.0f}% from yield")

    print("\nQ2  yield gap (rainfed peers, min area filter)")
    gap = yield_gap(crops)
    gap.to_csv(TAB / "yield_gap.csv")
    fig_yield_gap(gap)
    RESULTS["yield_gap"] = gap.round(2).to_dict("index")
    print(gap[["nigeria_t_ha", "best_peer", "best_peer_t_ha", "peer_median_t_ha",
               "n_peers", "gap_vs_best_pct", "gap_vs_median_pct"]].round(2).to_string())

    print("\nQ3  fertiliser context")
    RESULTS["fertiliser_kg_ha_latest"] = {k: round(v, 1) for k, v in fig_fertiliser(macro).items()}
    print(RESULTS["fertiliser_kg_ha_latest"])

    print("\nQ4  per-capita production")
    RESULTS["per_capita"] = fig_per_capita(crops, macro)
    print({k: round(v, 1) for k, v in RESULTS["per_capita"].items()})

    print("\nQ5  value of closing the gap to peer median")
    val = value_of_gap(crops, gap)
    val.to_csv(TAB / "value_of_closing_gap.csv", index=False)
    RESULTS["value_of_closing_gap"] = {
        "total_extra_tonnes": float(val.extra_tonnes.sum()),
        "total_value_usd": float(val.value_usd.sum(skipna=True)),
        "by_crop": val.set_index("crop").round(2).to_dict("index"),
    }
    print(val.round(1).to_string(index=False))
    print(f"  TOTAL: {val.extra_tonnes.sum()/1e6:.1f} m tonnes, "
          f"US${val.value_usd.sum(skipna=True)/1e9:.1f} bn/yr")

    with open(ROOT / "outputs" / "results.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=float)
    print("\nSaved outputs/results.json")


if __name__ == "__main__":
    main()
