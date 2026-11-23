"""Nigeria Crop Growth and Yield Analysis: present committed analysis outputs with context."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
st.set_page_config(page_title="Nigeria Crop Growth and Yield Analysis", page_icon="🌾", layout="wide")


@st.cache_data
def load_data():
    with (DATA / "headline.json").open(encoding="utf-8") as f:
        headline = json.load(f)
    with (DATA / "ml_results.json").open(encoding="utf-8") as f:
        ml = json.load(f)
    return (
        pd.read_csv(DATA / "decomposition.csv"),
        pd.read_csv(DATA / "yield_gap.csv"),
        headline,
        ml,
    )


try:
    dec, gap, headline, ml = load_data()
except (FileNotFoundError, ValueError, KeyError) as exc:
    st.error(f"Unable to load the saved analysis: {exc}. Check the data/processed folder.")
    st.stop()

st.title("Nigeria Crop Growth and Yield Analysis")
st.subheader("Has crop production grown through more harvested area, higher yields, or both?")
st.write(
    "See how harvested area and yield changed for eight crops in Nigeria. "
    "The analysis describes observed patterns; it does not establish what caused them."
)
st.info(
    "The dashboard uses saved results from FAOSTAT and World Bank data. "
    "The source data may be revised over time."
)

area_tab, peer_tab, methods_tab = st.tabs(["Area and yield", "Peer comparisons", "Method and limitations"])

with area_tab:
    st.header("How did area and yield change?")
    st.caption(
        "Comparison of three-year averages for 1990–1992 and 2021–2023. "
        "Yield is production divided by harvested area."
    )
    d = dec.sort_values("area_growth_pct")
    fig, ax = plt.subplots(figsize=(9, 5))
    pos = list(range(len(d)))
    ax.barh([i + 0.2 for i in pos], d["area_growth_pct"], height=0.4, label="Harvested area", color="#216b4a")
    ax.barh([i - 0.2 for i in pos], d["yield_growth_pct"], height=0.4, label="Yield per hectare", color="#bc7555")
    ax.set_yticks(pos, d["crop"])
    ax.axvline(0, color="#555555", linewidth=0.8)
    ax.set_xlabel("Change between the two periods (%)")
    ax.legend(frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.write(
        "The crops show different patterns. Compare the two bars for each crop: "
        "a positive area bar shows an increase in harvested area, while a positive yield bar "
        "shows an increase in production per hectare."
    )
    with st.expander("View the underlying crop comparisons"):
        cols = ["crop", "area_ha_start", "area_ha_end", "yield_t_ha_start", "yield_t_ha_end", "area_growth_pct", "yield_growth_pct"]
        st.dataframe(dec[cols].round(2), hide_index=True, use_container_width=True)
    st.caption("An increase in harvested area does not by itself show that new land was cleared.")

with peer_tab:
    st.header("How do yields compare with selected peers?")
    st.write(
        "For each crop, Nigeria is compared with selected African countries that meet "
        "the project's minimum harvested-area requirement. The countries vary by crop."
    )
    view = gap[["crop", "nigeria_t_ha", "peer_median_t_ha", "best_t_ha", "best_country", "qualifying_peers"]].copy()
    view.columns = ["Crop", "Nigeria (t/ha)", "Peer median (t/ha)", "Highest peer (t/ha)", "Highest peer country", "Number of peers"]
    st.dataframe(view.round(2), hide_index=True, use_container_width=True)
    st.caption(
        "Values are 2019–2023 averages. A qualifying peer's yield is a comparison, "
        "not necessarily an achievable target; countries differ in growing conditions."
    )
    st.write(
        "In the saved results, Nigeria is above the qualifying peer median for "
        f"{headline['yield_gap']['crops_above_peer_median']} of "
        f"{headline['yield_gap']['crops_compared']} crops. "
        "Some comparison groups are small, so the results apply only to these selected countries."
    )

with methods_tab:
    st.header("How the analysis works")
    st.markdown(f"""
**Production:** For each crop, production equals harvested area multiplied by yield per hectare.

**Period comparison:** The analysis compares average area and average yield in 1990–1992 with those in 2021–2023. The charts show what changed, not what caused the changes.

**Weighted index:** The analysis notebook also calculates a weighted index of crop-level changes and separates its log change into area and yield components. This is not the same as the percentage change in the sum of crop production tonnes. It shows how the changes add up, not what caused them.

**Peer selection:** A selected country qualifies as a peer for a crop if its average harvested area for that crop is at least 10% of Nigeria's over the reference window. The choice of peers and threshold affects results.

**Fertilizer analysis:** The project also looks at fertilizer use and cereal yields across countries. A relationship between them does not prove that one caused the other.

**Machine learning:** The repository compares a gradient boosting model with a last-known-yield baseline. After rebuilding the analysis from source data, model R² on log yield was {ml['r2_model_with_lag']:.4f} versus {ml['r2_best_baseline']:.4f} for the baseline. The difference is small. Some inputs come from the same year as the yield, and their availability when making a prediction is not established. This is not a tested real-time forecast.

**Data limitations:** Some figures are estimated or imputed where direct observations were unavailable. National averages hide regional and farm-level differences. These eight crops do not represent all food production, consumption, nutrition, or food security. Peer yield differences do not automatically identify achievable improvements.
    """)
    st.caption("Sources: FAOSTAT Crops and Livestock Products; World Bank World Development Indicators. See the repository README and data/raw/SOURCES.md.")
