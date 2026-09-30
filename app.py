"""
Nigeria Yield Gap Explorer, Streamlit dashboard.

Run locally:   streamlit run app.py
Deploy free:   push to GitHub -> share.streamlit.io -> pick repo -> app.py
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

ROOT = pathlib.Path(__file__).resolve().parent
PROC = ROOT / "data" / "processed"
OUTP = ROOT / "outputs"

GREEN, GOLD, CLAY, INK, GREY = "#1f6b45", "#c8892c", "#a8543a", "#0d1b14", "#8a958e"

st.set_page_config(page_title="Nigeria Yield Gap Explorer",
                   page_icon="🌾", layout="wide")

st.markdown("""
<style>
  .block-container{padding-top:2.2rem;max-width:1250px}
  h1,h2,h3{letter-spacing:-.02em}
  [data-testid="stMetricValue"]{font-size:1.75rem;color:#1f6b45}
  .caption{color:#5d6b62;font-size:.86rem}
  .src{background:#f2efe6;border-left:3px solid #1f6b45;padding:.7rem 1rem;
       border-radius:6px;font-size:.84rem;color:#33443a}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    crops = pd.read_csv(PROC / "crop_panel.csv")
    macro = pd.read_csv(PROC / "macro_panel.csv")
    res = json.loads((OUTP / "results.json").read_text())
    mres = json.loads((OUTP / "model_results.json").read_text())
    gap = pd.read_csv(OUTP / "tables" / "yield_gap.csv", index_col=0)
    dec = pd.read_csv(OUTP / "tables" / "growth_decomposition.csv")
    return crops, macro, res, mres, gap, dec


crops, macro, res, mres, gap, dec = load()

# ---------------------------------------------------------------- header
st.title("🌾 Nigeria Yield Gap Explorer")
st.markdown(
    "**Is Nigeria producing more food because farmers farm better, or just because "
    "they farm more land?** An analysis of 60 years of FAOSTAT and World Bank data "
    "covering eight staple crops."
)

d = res["decomposition"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Growth from land expansion", f"{d['share_from_area_pct']:.0f}%",
          help="Production-share weighted, 1990-2023")
c2.metric("Growth from yield gains", f"{d['share_from_yield_pct']:.0f}%",
          delta="yields fell on aggregate", delta_color="inverse")
c3.metric("Fertiliser use", f"{res['fertiliser_kg_ha_latest']['Nigeria']:.0f} kg/ha",
          delta=f"vs Ghana {res['fertiliser_kg_ha_latest']['Ghana']:.0f}",
          delta_color="inverse")
c4.metric("Output per person vs 2006 peak",
          f"{res['per_capita']['decline_from_peak_pct']:.0f}%",
          delta_color="inverse")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📉 The core finding", "🌍 Yield gap by crop", "🧪 Fertiliser scenarios",
     "📈 Explore the data", "📋 Method & sources"])

# ================================================================ TAB 1
with tab1:
    st.subheader("Where Nigeria's food output growth actually came from, 1990-2023")
    left, right = st.columns([1.5, 1])
    with left:
        dd = dec.sort_values("production_growth_pct")
        fig = go.Figure()
        fig.add_bar(y=dd.crop, x=dd.area_growth_pct, name="Area harvested",
                    orientation="h", marker_color=CLAY)
        fig.add_bar(y=dd.crop, x=dd.yield_growth_pct, name="Yield",
                    orientation="h", marker_color=GREEN)
        fig.update_layout(barmode="group", height=430, template="simple_white",
                          xaxis_title="Change 1990-2023 (%)",
                          legend=dict(orientation="h", y=1.12),
                          margin=dict(l=10, r=10, t=40, b=10))
        fig.add_vline(x=0, line_width=1.5, line_color=INK)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown(f"""
### The headline

Between 1990 and 2023, Nigeria's output of eight staple crops grew substantially.

**But {d['share_from_area_pct']:.0f}% of that growth came from planting more
hectares, and the yield contribution was
{d['share_from_yield_pct']:.0f}%, i.e. average yields *fell*.**

Cassava yields dropped **{abs(dec.set_index('crop').loc['Cassava','yield_growth_pct']):.0f}%**
while cassava area grew **{dec.set_index('crop').loc['Cassava','area_growth_pct']:.0f}%**.
Yam is the same story.

**Maize is the exception**, yields up
{dec.set_index('crop').loc['Maize','yield_growth_pct']:.0f}% on almost flat area.
That is what intensification looks like, and it shows it is possible.

Growth by land expansion has a hard ceiling: it competes with forest, grazing
land and settlements, and it raises emissions. Growth by yield does not.
        """)
    st.info("**Why this matters for policy and investment:** an input, seed or extension "
            "programme that raises yield on existing land is doing something structurally "
            "different from a programme that brings new land into cultivation, and only "
            "one of the two can continue indefinitely.")

# ================================================================ TAB 2
with tab2:
    st.subheader("How far is Nigeria from comparable African producers?")
    st.markdown('<div class="caption">Rainfed African peers only. Egypt and South Africa '
                'are excluded from the benchmark (irrigated, high-input systems) and a '
                'country must harvest at least 100,000 ha of the crop to qualify, '
                'without that filter, small-area outliers look like world leaders.</div>',
                unsafe_allow_html=True)
    st.write("")

    g = gap.sort_values("gap_vs_best_pct", ascending=True)
    fig = go.Figure()
    for i, (crop, r) in enumerate(g.iterrows()):
        fig.add_trace(go.Scatter(x=[r.nigeria_t_ha, r.best_peer_t_ha], y=[crop, crop],
                                 mode="lines", line=dict(color=GREY, width=2),
                                 showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g.nigeria_t_ha, y=g.index, mode="markers", name="Nigeria",
                             marker=dict(color=GREEN, size=14)))
    fig.add_trace(go.Scatter(x=g.peer_median_t_ha, y=g.index, mode="markers",
                             name="Peer median",
                             marker=dict(color=GOLD, size=10, symbol="diamond")))
    fig.add_trace(go.Scatter(x=g.best_peer_t_ha, y=g.index, mode="markers",
                             name="Best rainfed peer", marker=dict(color=CLAY, size=14),
                             text=g.best_peer, hovertemplate="%{text}: %{x:.2f} t/ha"))
    fig.update_layout(height=430, template="simple_white",
                      xaxis_title="Yield, tonnes per hectare (2019-2023 average)",
                      legend=dict(orientation="h", y=1.12),
                      margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    v = res["value_of_closing_gap"]
    a, b = st.columns(2)
    a.metric("Extra output if Nigeria hit the peer MEDIAN yield",
             f"{v['total_extra_tonnes']/1e6:.0f} m tonnes/yr")
    b.metric("Indicative gross value", f"US${v['total_value_usd']/1e9:.0f} bn/yr")
    st.caption("On existing harvested area, holding area constant. Cassava and yam "
               "producer prices are imputed from the peer-group median because FAOSTAT "
               "has no Nigerian series for them, treat the dollar figure as an "
               "order-of-magnitude, not a forecast.")
    st.dataframe(
        gap[["nigeria_t_ha", "best_peer", "best_peer_t_ha", "peer_median_t_ha",
             "n_peers", "gap_vs_best_pct", "gap_vs_median_pct"]].round(2),
        use_container_width=True)
    st.caption("Negative gap vs median = Nigeria already above the peer median for that crop.")

# ================================================================ TAB 3
with tab3:
    st.subheader("What would more fertiliser actually buy?")
    fe = mres["panel_fe"]
    st.markdown(f"""
Estimated from a **two-way fixed-effects panel regression** on
**{fe['n_obs']:,} country-year observations across {fe['n_countries']} countries
({fe['years']})**, with country and year fixed effects and standard errors
clustered by country:

> **Elasticity of cereal yield to fertiliser intensity = {fe['elasticity_fertiliser']:.3f}**
> (95% CI {fe['ci95_low']:.3f}, {fe['ci95_high']:.3f}, p = {fe['p_value']:.1g})

A 10% rise in fertiliser per hectare is associated with a
**{fe['elasticity_fertiliser']*10:.2f}% rise in cereal yield**, within a country, net of
global year effects.
    """)

    ng = macro[(macro.country == "Nigeria")].dropna(subset=["fert_kg_ha"]).sort_values("year")
    f_now = ng.fert_kg_ha.tail(3).mean()
    y_now = ng.cereal_yield_kg_ha.tail(3).mean()
    area = ng.cereal_area_ha.tail(3).mean()

    st.write("")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        target = st.slider("Fertiliser intensity, kg nutrient per hectare",
                           float(round(f_now, 1)), 150.0, 36.0, 1.0)
        elast = st.select_slider(
            "Which elasticity estimate?",
            options=["Low-input subsample (conservative)", "Full sample (headline)"],
            value="Full sample (headline)")
        e = (fe["elasticity_low_input_subsample"]
             if elast.startswith("Low") else fe["elasticity_fertiliser"])
        mult = (target / f_now) ** e
        y_new = y_now * mult
        extra_t = (y_new - y_now) * area / 1000

        st.metric("Predicted cereal yield", f"{y_new/1000:.2f} t/ha",
                  delta=f"{(mult-1)*100:+.1f}%")
        st.metric("Extra cereal production", f"{extra_t/1e6:+.2f} m tonnes/yr")
        st.metric("Fertiliser needed",
                  f"{(target-f_now)*ng.arable_land_ha.tail(1).values[0]/1e9:+.2f} m tonnes nutrient/yr")
    with c2:
        xs = np.linspace(f_now, 150, 120)
        for label, ee, col in [("Full sample", fe["elasticity_fertiliser"], GREEN),
                               ("Low-input subsample", fe["elasticity_low_input_subsample"], GOLD)]:
            ys = y_now * (xs / f_now) ** ee / 1000
            fig = fig if label != "Full sample" else go.Figure()
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=label,
                                     line=dict(color=col, width=3)))
        fig.add_vline(x=f_now, line_dash="dot", line_color=GREY,
                      annotation_text=f"Nigeria today ({f_now:.0f})")
        fig.add_vline(x=target, line_dash="dash", line_color=CLAY,
                      annotation_text="your scenario")
        for nm, val in [("Ghana", 36.1), ("Ethiopia", 37.8), ("World avg", 120)]:
            fig.add_vline(x=val, line_width=1, line_color="#ccc",
                          annotation_text=nm, annotation_font_size=9)
        fig.update_layout(height=400, template="simple_white",
                          xaxis_title="kg nutrient per ha arable",
                          yaxis_title="Predicted cereal yield, t/ha",
                          legend=dict(orientation="h", y=1.12),
                          margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.warning(
        f"**Read this before quoting the numbers.** The low-input subsample elasticity "
        f"({fe['elasticity_low_input_subsample']:.3f}) is *lower* than the full-sample "
        f"estimate ({fe['elasticity_fertiliser']:.3f}). That is consistent with the "
        "agronomic literature: in low-input systems, fertiliser response is constrained "
        "by complementary factors, soil organic carbon, seed quality, moisture, timing "
        "and extension. Fertiliser alone is not a yield strategy. This is an association "
        "estimated from observational panel data with fixed effects, not a randomised "
        "agronomic trial, so treat it as a planning envelope rather than a causal dose-response curve.")

# ================================================================ TAB 4
with tab4:
    st.subheader("Explore the underlying data")
    c1, c2 = st.columns(2)
    crop_sel = c1.selectbox("Crop", sorted(crops.crop.unique()),
                            index=sorted(crops.crop.unique()).index("Maize"))
    countries = c2.multiselect("Countries", sorted(crops.country.unique()),
                               default=["Nigeria", "Ghana", "Ethiopia"])
    metric = st.radio("Metric", ["yield_t_ha", "area_ha", "production_t"],
                      horizontal=True,
                      format_func=lambda x: {"yield_t_ha": "Yield (t/ha)",
                                             "area_ha": "Area harvested (ha)",
                                             "production_t": "Production (t)"}[x])
    d2 = crops[(crops.crop == crop_sel) & crops.country.isin(countries)]
    fig = px.line(d2, x="year", y=metric, color="country", template="simple_white",
                  color_discrete_sequence=[GREEN, GOLD, CLAY, GREY, "#4c7f9b"])
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(d2.sort_values("year", ascending=False).head(30).round(3),
                 use_container_width=True)

# ================================================================ TAB 5
with tab5:
    st.subheader("Method, sources and limitations")
    st.markdown("""
#### Data
| Source | What | Access |
|---|---|---|
| FAOSTAT, Production_Crops_Livestock (Africa) | Area harvested, production, yield by country-crop-year, 1961-2024 | Open bulk download |
| FAOSTAT, Inputs_FertilizersNutrient (Africa) | N, P₂O₅, K₂O agricultural use, tonnes | Open bulk download |
| FAOSTAT, Prices (Africa) | Producer prices, USD/tonne | Open bulk download |
| World Bank WDI API | Cereal yield, fertiliser kg/ha, arable land, population, rural share | Open API |

#### Method
1. **Cleaning**, FAOSTAT bulk files are wide (one column per year plus flag/note columns); melted to tidy long format. Yield is recomputed as production ÷ area so the unit is unambiguous and internally consistent. Implausible values (<0.05 or >100 t/ha) dropped.
2. **Growth decomposition**, since P = A × Y, ln P = ln A + ln Y, so log growth splits exactly into an area and a yield component. Endpoints are 3-year averages to remove single-season weather noise. Aggregated across crops with Törnqvist (production-share) weights.
3. **Yield-gap benchmarking**, rainfed African peers only; minimum 100,000 ha harvested to qualify as a benchmark; Egypt and South Africa reported separately as the irrigated frontier.
4. **Panel fixed effects**, ln(yield) on ln(fertiliser) with country and year fixed effects, SEs clustered by country. Re-estimated on the low-input half of the sample as a robustness check.
5. **Gradient boosting**, validated on a **temporal** holdout (train < 2013, test ≥ 2013), never a random split, because random splitting panel data leaks future information and inflates R².

#### Limitations, stated plainly
- **National averages hide everything.** A 2 t/ha national maize yield is an average over agro-ecological zones, farm sizes and management. Plot-level survey data (LSMS-ISA) is the right tool for household-level questions; see `LSMS_EXTENSION.md` in the repo for the extension path.
- **Association, not causation.** Fixed effects absorb time-invariant country differences and global year shocks, but fertiliser use is not randomly assigned. Countries that apply more fertiliser also tend to have better roads, credit and extension.
- **FAOSTAT is partly imputed.** Many African production figures are FAO estimates rather than measured censuses. Flags are retained in the raw files.
- **Producer prices are incomplete.** Nigeria has no FAOSTAT cassava or yam producer price series in this release; the peer median is imputed and labelled as such.
- **Area and management held constant** in the scenario engine, which is deliberately conservative.
    """)
    st.markdown('<div class="src">Built by <b>Halimat H. Fakorede</b>, '
                'Agricultural Data Scientist &amp; Operations Analyst · '
                'github.com/HalimatFakorede</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("Data: FAOSTAT (2024/25 releases) and World Bank WDI. "
           "Analysis and dashboard by Halimat H. Fakorede.")
