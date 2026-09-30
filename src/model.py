"""
Project 1, Step 3: Modelling.

Two complementary models, deliberately:

  A) PANEL FIXED-EFFECTS REGRESSION  (the "why" model, interpretable, quasi-causal)
       ln(cereal yield) = b * ln(fertiliser kg/ha) + country FE + year FE + controls
     Country fixed effects absorb every time-invariant difference between countries
     (soil, climate zone, institutions). Year fixed effects absorb global shocks
     (oil prices, weather years, technology diffusion). What is left is: within a
     country, over time, when fertiliser intensity rises, what happens to yield?
     b is a YIELD ELASTICITY. Standard errors are clustered by country because
     observations within a country are serially correlated.

  B) GRADIENT BOOSTING  (the "how much / prediction" model)
     Same features, no linearity assumption. Validated on a TEMPORAL holdout
     (train <= 2012, test >= 2013) rather than a random split, because a random
     split on panel data leaks the future into the training set and inflates R2.

Then: a scenario engine that converts the elasticity into tonnes and dollars for
Nigeria under counterfactual fertiliser intensities.

Outputs: outputs/model_results.json, outputs/figures/05*.png, 06*.png, outputs/tables/*
Run:  python src/model.py
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.inspection import permutation_importance

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"
GREEN, GOLD, CLAY, INK, GREY = "#1f6b45", "#c8892c", "#a8543a", "#0d1b14", "#8a958e"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 160, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": .25, "grid.linestyle": "--",
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlepad": 12,
})

SPLIT_YEAR = 2013
OUT: dict = {}


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, bbox_inches="tight"); plt.close(fig)
    print(f"  figure -> outputs/figures/{name}")


# ---------------------------------------------------------------------------
def build_model_frame() -> pd.DataFrame:
    """Global country-year panel of cereal yield and its drivers."""
    m = pd.read_csv(PROC / "macro_panel.csv")
    d = m[["iso3", "country", "year", "cereal_yield_kg_ha", "fert_kg_ha",
           "arable_land_ha", "cereal_area_ha", "agri_valueadd_pct_gdp",
           "rural_pop_pct", "population"]].copy()
    d = d.dropna(subset=["cereal_yield_kg_ha", "fert_kg_ha"])
    d = d[(d.cereal_yield_kg_ha > 100) & (d.fert_kg_ha > 0.1)]   # drop implausible

    d["ln_yield"] = np.log(d.cereal_yield_kg_ha)
    d["ln_fert"] = np.log(d.fert_kg_ha)
    d["ln_area"] = np.log(d.cereal_area_ha.clip(lower=1))
    d["ln_pop"] = np.log(d.population.clip(lower=1))
    # keep countries with enough within-country variation to identify the FE model
    keep = d.groupby("iso3").size()
    d = d[d.iso3.isin(keep[keep >= 15].index)]
    return d.dropna(subset=["ln_yield", "ln_fert", "ln_area"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
def panel_fe(d: pd.DataFrame) -> dict:
    """Two-way fixed effects OLS with country-clustered standard errors."""
    X = pd.get_dummies(d[["iso3", "year"]].astype({"year": "category"}),
                       columns=["iso3", "year"], drop_first=True, dtype=float)
    X["ln_fert"] = d.ln_fert.values
    X["ln_area"] = d.ln_area.values
    X["rural_pop_pct"] = d.rural_pop_pct.fillna(d.rural_pop_pct.median()).values
    X = sm.add_constant(X)
    model = sm.OLS(d.ln_yield.values, X).fit(
        cov_type="cluster", cov_kwds={"groups": d.iso3.values})

    b = model.params["ln_fert"]
    se = model.bse["ln_fert"]
    res = {
        "n_obs": int(model.nobs),
        "n_countries": int(d.iso3.nunique()),
        "years": f"{int(d.year.min())}-{int(d.year.max())}",
        "elasticity_fertiliser": float(b),
        "std_error_clustered": float(se),
        "t_stat": float(b / se),
        "p_value": float(model.pvalues["ln_fert"]),
        "ci95_low": float(b - 1.96 * se), "ci95_high": float(b + 1.96 * se),
        "within_r2": float(model.rsquared),
        "interpretation": (f"A 10% increase in fertiliser intensity is associated with a "
                           f"{b*10:.2f}% increase in cereal yield, within country, "
                           f"net of global year effects."),
    }
    print(f"  FE elasticity = {b:.4f} (SE {se:.4f}, p={res['p_value']:.2g}), "
          f"N={res['n_obs']:,} over {res['n_countries']} countries")

    # robustness: Sub-Saharan-only subsample would need a region map; instead
    # re-estimate on the low-input half of the sample (fert < median), the part
    # of the curve Nigeria actually sits on.
    lo = d[d.fert_kg_ha < d.fert_kg_ha.median()]
    Xl = pd.get_dummies(lo[["iso3", "year"]].astype({"year": "category"}),
                        columns=["iso3", "year"], drop_first=True, dtype=float)
    Xl["ln_fert"] = lo.ln_fert.values
    Xl["ln_area"] = lo.ln_area.values
    Xl = sm.add_constant(Xl)
    ml = sm.OLS(lo.ln_yield.values, Xl).fit(cov_type="cluster",
                                            cov_kwds={"groups": lo.iso3.values})
    res["elasticity_low_input_subsample"] = float(ml.params["ln_fert"])
    res["n_obs_low_input"] = int(ml.nobs)
    print(f"  low-input subsample elasticity = {ml.params['ln_fert']:.4f} "
          f"(N={int(ml.nobs):,})")
    return res


# ---------------------------------------------------------------------------
def gbm(d: pd.DataFrame) -> dict:
    feats = ["ln_fert", "ln_area", "rural_pop_pct", "agri_valueadd_pct_gdp",
             "ln_pop", "year"]
    dd = d.copy()
    for c in feats:
        dd[c] = dd[c].fillna(dd[c].median())

    tr, te = dd[dd.year < SPLIT_YEAR], dd[dd.year >= SPLIT_YEAR]
    m = GradientBoostingRegressor(n_estimators=400, max_depth=3,
                                  learning_rate=0.05, subsample=0.9,
                                  random_state=42)
    m.fit(tr[feats], tr.ln_yield)
    pred = m.predict(te[feats])
    r2, mae = r2_score(te.ln_yield, pred), mean_absolute_error(te.ln_yield, pred)

    # baseline: predict each country's own last training-period mean
    base = tr.groupby("iso3").ln_yield.mean()
    bpred = te.iso3.map(base).fillna(tr.ln_yield.mean())
    r2b = r2_score(te.ln_yield, bpred)

    pi = permutation_importance(m, te[feats], te.ln_yield, n_repeats=20,
                                random_state=42, scoring="r2")
    imp = (pd.DataFrame({"feature": feats, "importance": pi.importances_mean,
                         "sd": pi.importances_std})
             .sort_values("importance", ascending=False))
    imp.to_csv(TAB / "feature_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.barh(imp.feature[::-1], imp.importance[::-1],
            xerr=imp.sd[::-1], color=GREEN, error_kw=dict(ecolor=GREY, lw=1))
    ax.set_xlabel("Permutation importance (drop in test R² when shuffled)")
    ax.set_title("What predicts national cereal yield?\n"
                 f"Gradient boosting, temporal holdout (train <{SPLIT_YEAR}, test ≥{SPLIT_YEAR})",
                 loc="left")
    save(fig, "05_feature_importance.png")

    print(f"  GBM test R2 = {r2:.3f} (baseline {r2b:.3f}), MAE(log) = {mae:.3f}")
    return {"test_r2": float(r2), "baseline_r2": float(r2b),
            "test_mae_log": float(mae),
            "test_mae_pct": float((np.exp(mae) - 1) * 100),
            "n_train": int(len(tr)), "n_test": int(len(te)),
            "split_year": SPLIT_YEAR,
            "top_features": imp.head(4).set_index("feature")["importance"].round(4).to_dict()}


# ---------------------------------------------------------------------------
def scenarios(d: pd.DataFrame, elasticity: float) -> pd.DataFrame:
    """
    Counterfactual: raise Nigeria's fertiliser intensity to peer levels.
    Yield multiplier = (F_new / F_now) ** elasticity      [log-log model]
    Applied to current cereal production; deliberately conservative because it
    holds area, seed and management constant.
    """
    ng = d[d.iso3 == "NGA"].sort_values("year").tail(3)
    f_now = ng.fert_kg_ha.mean()
    y_now = ng.cereal_yield_kg_ha.mean()
    area = ng.cereal_area_ha.mean()
    prod_now = y_now * area / 1000                      # tonnes

    targets = {"Nigeria today": f_now, "Ghana level": 36.1, "Ethiopia level": 37.8,
               "Kenya level": 33.2, "World average (~120)": 120.0,
               "South Africa level": 101.4}
    rows = []
    for name, f_new in targets.items():
        mult = (f_new / f_now) ** elasticity
        y_new = y_now * mult
        prod_new = y_new * area / 1000
        rows.append({"scenario": name, "fert_kg_ha": f_new,
                     "yield_kg_ha": y_new,
                     "yield_change_pct": (mult - 1) * 100,
                     "production_mt": prod_new / 1e6,
                     "extra_production_mt": (prod_new - prod_now) / 1e6})
    s = pd.DataFrame(rows)
    s.to_csv(TAB / "fertiliser_scenarios.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    c = [GREEN if r.scenario == "Nigeria today" else GOLD for r in s.itertuples()]
    ax.bar(s.scenario, s.yield_kg_ha / 1000, color=c, width=.62)
    for i, r in enumerate(s.itertuples()):
        ax.text(i, r.yield_kg_ha / 1000 + .03,
                f"{r.yield_kg_ha/1000:.2f}\n({r.yield_change_pct:+.0f}%)",
                ha="center", fontsize=8.5, color=INK)
    ax.set_ylabel("Predicted cereal yield, t/ha")
    ax.set_title("If Nigeria used fertiliser like its peers\n"
                 f"Log-log elasticity = {elasticity:.3f}, area and management held constant",
                 loc="left")
    plt.setp(ax.get_xticklabels(), rotation=18, ha="right", fontsize=8.5)
    ax.set_ylim(0, s.yield_kg_ha.max() / 1000 * 1.22)
    save(fig, "06_fertiliser_scenarios.png")

    print(s.round(2).to_string(index=False))
    return s


def main():
    d = build_model_frame()
    print(f"Model frame: {len(d):,} country-year rows, {d.iso3.nunique()} countries, "
          f"{int(d.year.min())}-{int(d.year.max())}")
    OUT["sample"] = {"n_rows": int(len(d)), "n_countries": int(d.iso3.nunique()),
                     "year_min": int(d.year.min()), "year_max": int(d.year.max())}

    print("\nA) Panel fixed-effects regression")
    fe = panel_fe(d); OUT["panel_fe"] = fe

    print("\nB) Gradient boosting (temporal holdout)")
    OUT["gbm"] = gbm(d)

    print("\nC) Scenario engine")
    s = scenarios(d, fe["elasticity_fertiliser"])
    OUT["scenarios"] = s.round(3).to_dict("records")

    with open(ROOT / "outputs" / "model_results.json", "w") as f:
        json.dump(OUT, f, indent=2, default=float)
    print("\nSaved outputs/model_results.json")


if __name__ == "__main__":
    main()
