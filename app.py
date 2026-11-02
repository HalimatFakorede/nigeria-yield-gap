"""Nigeria Yield Gap dashboard. Reads the processed files, does no heavy work."""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import config as C  # noqa: E402

plt.rcParams.update(C.PLOT_STYLE)
st.set_page_config(page_title="Nigeria Yield Gap", page_icon="🌾", layout="wide")


@st.cache_data
def load_csv(name):
    return pd.read_csv(C.PROCESSED / name)


@st.cache_data
def load_json(name):
    with open(C.PROCESSED / name) as f:
        return json.load(f)


try:
    dec      = load_csv("decomposition.csv")
    per_cap  = load_csv("nigeria_per_capita.csv")
    gap      = load_csv("yield_gap.csv")
    fert     = load_csv("fertilizer.csv")
    headline = load_json("headline.json")
    model    = load_json("model_results.json")
    ml       = load_json("ml_results.json")
except FileNotFoundError as e:
    st.error(f"Missing {e.filename}. Run the notebooks in order, 01 to 06.")
    st.stop()

peak = per_cap.loc[per_cap["kg_per_person"].idxmax()]
latest = per_cap.iloc[-1]
yg = headline["yield_gap"]
naive = headline["naive_split"]

st.title("Nigeria Yield Gap")
st.markdown(
    f"Nigeria's output of eight staple crops grew "
    f"**{headline['production_growth_pct']:.0f}%** between {headline['window']['start']} "
    f"and {headline['window']['end']}, almost entirely by planting more land. "
    f"Food per person peaked in {int(peak['year'])}."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Production growth", f"{headline['production_growth_pct']:.0f}%")
c2.metric("From more land", f"{headline['share_from_area_pct']:.0f}%")
c3.metric("From better yield", f"{headline['share_from_yield_pct']:.0f}%")
c4.metric("Food per person since peak",
          f"{(latest['kg_per_person'] / peak['kg_per_person'] - 1) * 100:.1f}%")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Where the growth came from", "Food per person", "The yield gap", "Method"]
)

# ---------------------------------------------------------------- tab 1
with tab1:
    st.subheader("Area grew. Yield mostly did not.")

    d = dec.sort_values("area_growth_pct")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    y, h = np.arange(len(d)), 0.38
    ax.barh(y + h / 2, d["area_growth_pct"], h, color=C.GREEN, label="Area harvested")
    ax.barh(y - h / 2, d["yield_growth_pct"], h, color=C.CLAY, label="Yield per hectare")
    ax.axvline(0, color=C.INK, lw=1)
    for i, (a, b) in enumerate(zip(d["area_growth_pct"], d["yield_growth_pct"])):
        ax.text(a + (8 if a >= 0 else -8), i + h / 2, f"{a:+.0f}%",
                va="center", ha="left" if a >= 0 else "right", fontsize=8)
        ax.text(b + (8 if b >= 0 else -8), i - h / 2, f"{b:+.0f}%",
                va="center", ha="left" if b >= 0 else "right", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(d["crop"])
    ax.set_xlabel(f"Change {headline['window']['start']} to {headline['window']['end']}, %")
    ax.set_xlim(-130, 480)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    st.pyplot(fig)

    maize = dec.loc[dec["crop"] == "Maize"].iloc[0]
    st.markdown(
        f"Maize is the exception, with yield up {maize['yield_growth_pct']:.0f}% on "
        f"{maize['area_growth_pct']:.0f}% more land. Cassava and yam, the two biggest "
        "crops, expanded a lot while their yields fell."
    )

    with st.expander(f"Why {headline['share_from_area_pct']:.0f}% and not "
                     f"{naive['land_applied_first_pct']:.0f}%"):
        st.markdown(f"""
Production is area times yield, so when both change, part of the growth belongs to both
at once. A simple before and after split has to give that part to one side, and the
answer depends on which change you apply first.

| Order | Share from land |
|---|---|
| land first | {naive['land_applied_first_pct']:.1f}% |
| yield first | {naive['yield_applied_first_pct']:.1f}% |

The shared part is {naive['interaction_tonnes']:,} tonnes, which is
{abs(naive['interaction_share_of_gain_pct']):.0f}% of the total gain. Neither answer can
be defended when the choice moves it that far.

Logs turn the multiplication into an addition, and an addition has no order. Crops are
then weighted by their average share of production. That gives
{headline['share_from_area_pct']:.1f}%.
        """)

    with st.expander("Does the choice of years matter"):
        es = headline["endpoint_sensitivity"]
        st.markdown(f"""
The start and end points are {headline['window']['endpoint_years_averaged']} year
averages. Using single years instead moves the answer between
{es['single_year_min_pct']:.1f}% and {es['single_year_max_pct']:.1f}%, just depending on
which years you pick.
        """)

    with st.expander("The numbers"):
        st.dataframe(
            dec[["crop", "area_ha_start", "area_ha_end", "yield_t_ha_start",
                 "yield_t_ha_end", "area_growth_pct", "yield_growth_pct", "weight"]].round(3),
            width="stretch", hide_index=True,
        )

# ---------------------------------------------------------------- tab 2
with tab2:
    st.subheader("Food produced per Nigerian")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(per_cap["year"], per_cap["kg_per_person"], color=C.GREEN, lw=2.3)
    ax.scatter([peak["year"]], [peak["kg_per_person"]], s=60, color=C.CLAY, zorder=5)
    ax.annotate(f"peak {peak['kg_per_person']:.0f} kg in {int(peak['year'])}",
                xy=(peak["year"], peak["kg_per_person"]),
                xytext=(peak["year"] - 13, peak["kg_per_person"] + 40),
                fontsize=9, color=C.CLAY, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C.CLAY, lw=1.1))
    ax.set_ylabel("kg per person per year")
    ax.set_ylim(400, 900)
    fig.tight_layout()
    st.pyplot(fig)

    a, b, c = st.columns(3)
    a.metric(f"{int(per_cap['year'].iloc[0])}", f"{per_cap['kg_per_person'].iloc[0]:.0f} kg")
    b.metric(f"{int(peak['year'])} peak", f"{peak['kg_per_person']:.0f} kg")
    c.metric(f"{int(latest['year'])}", f"{latest['kg_per_person']:.0f} kg",
             f"{(latest['kg_per_person'] / peak['kg_per_person'] - 1) * 100:.1f}% vs peak")

    recent = per_cap[per_cap["year"] >= 2010]["kg_per_person"]
    st.markdown(
        f"Production tripled but the population more than doubled. The line is bumpy: "
        f"since 2010 it has moved between {recent.min():.0f} and {recent.max():.0f} kg, "
        f"and 2018 came within 3% of the peak. So output per person stopped improving "
        "rather than collapsed."
    )

# ---------------------------------------------------------------- tab 3
with tab3:
    st.subheader("How far behind is Nigeria?")

    st.caption(
        f"A country only counts as a peer for a crop if it farms at least "
        f"{yg['min_peer_area_share']:.0%} as much of it as Nigeria. Without that, Niger "
        "sets the cassava target on 23,000 hectares against Nigeria's 9.9 million."
    )

    g = gap.sort_values("upside_t")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    y = np.arange(len(g))
    for i, r in enumerate(g.itertuples()):
        ax.plot([min(r.nigeria_t_ha, r.best_t_ha), max(r.nigeria_t_ha, r.best_t_ha)],
                [i, i], color=C.GREY, lw=1.3, zorder=1)
    ax.scatter(g["nigeria_t_ha"], y, s=85, color=C.GREEN, zorder=3, label="Nigeria")
    ax.scatter(g["peer_median_t_ha"], y, s=50, color=C.GOLD, zorder=3, label="Peer median")
    ax.scatter(g["best_t_ha"], y, s=85, color=C.CLAY, zorder=3, label="Best peer")
    for i, r in enumerate(g.itertuples()):
        ax.text(r.best_t_ha + 0.5, i, r.best_country, va="center", fontsize=8, color=C.CLAY)
    ax.set_yticks(y)
    ax.set_yticklabels(g["crop"])
    ax.set_xlabel(f"Yield, tonnes per hectare, {yg['reference_window'][0]} to "
                  f"{yg['reference_window'][1]} average")
    ax.set_xlim(0, 30)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    st.pyplot(fig)

    cassava = gap.loc[gap["crop"] == "Cassava"].iloc[0]
    st.markdown(
        f"Nigeria beats the peer median on {yg['crops_above_peer_median']} of "
        f"{yg['crops_compared']} crops and leads on "
        f"{' and '.join(yg['crops_leading_best_peer']).lower()}.\n\n"
        f"The gap is cassava. {cassava['nigeria_t_ha']:.1f} t/ha against "
        f"{cassava['best_t_ha']:.1f} in {cassava['best_country']}, on Nigeria's biggest "
        f"crop by area. That one crop is {yg['cassava_share_of_upside_pct']}% of the gap, "
        f"about {yg['total_upside_tonnes'] / 1e6:.0f} million tonnes."
    )

    st.markdown("##### Fertilizer use")
    f = fert.sort_values("fert_kg_ha")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.barh(f["country"], f["fert_kg_ha"],
            color=[C.CLAY if c_ == "Nigeria" else C.GREY for c_ in f["country"]])
    ax.set_xscale("log")
    ax.set_xlabel(f"kg per hectare of arable land, {yg['reference_window'][0]} to "
                  f"{yg['reference_window'][1]} average")
    fig.tight_layout()
    st.pyplot(fig)

    st.markdown(
        f"Nigeria uses less fertilizer than almost every peer. That fits with the low "
        f"yields, but a fixed effects regression across {model['n_countries']} countries "
        f"puts the elasticity at only {model['elasticity']:.3f}, and "
        f"{model['elasticity_low_input']:.3f} for low input countries like Nigeria. "
        f"So 10% more fertilizer goes with about "
        f"{model['elasticity_low_input'] * 10:.1f}% more yield."
    )

    with st.expander("The numbers"):
        st.dataframe(gap.round(2), width="stretch", hide_index=True)

# ---------------------------------------------------------------- tab 4
with tab4:
    st.subheader("Method")

    st.markdown(f"""
**Data.** FAOSTAT Production Crops and Livestock (Africa), and World Bank WDI through
their API. {yg['crops_compared']} crops, {len(C.PEERS)} countries, 1961 to 2024.

**Start and end points** are {headline['window']['endpoint_years_averaged']} year
averages. Single years move the headline between
{headline['endpoint_sensitivity']['single_year_min_pct']:.0f}% and
{headline['endpoint_sensitivity']['single_year_max_pct']:.0f}%.

**Yield** is worked out from production and area rather than taken from the published
column, then checked against it. They agree to within 0.4%.

**The split uses logs**, because production is area times yield and a simple split
depends on which change you apply first.

**The model** is two way fixed effects OLS, {model['n_obs']:,} rows,
{model['n_countries']} countries, errors clustered by country.

**It rebuilds from nothing.** Delete the processed data and rerun the notebooks.
    """)

    st.markdown("##### Limits")
    st.markdown(f"""
- A lot of the Nigerian data is estimated rather than measured. Long run trends mean
  something, single years do not.
- The {yg['min_peer_area_share']:.0%} peer cut-off is a judgement. It is in
  `src/config.py` so it can be changed and rerun.
- The fertilizer results are associations, not causes. Without fixed effects the
  elasticity looks like {model['elasticity_no_fixed_effects']:.3f} instead of
  {model['elasticity']:.3f}.
- The effect is bigger where input use is already high
  ({model['elasticity_high_input']:.3f}) than where it is low
  ({model['elasticity_low_input']:.3f}), so fertilizer on its own is probably not enough.
- A gradient boosting model scored {ml['r2_model_with_lag']:.3f} against
  {ml['r2_best_baseline']:.3f} for just assuming each country stays where it was.
- Egypt and South Africa are here to show the best case, not as a target.
- These are national averages, which hide a lot in a country this size.
    """)

    st.caption("Halimat H. Fakorede. Sources: FAOSTAT, World Bank WDI.")
