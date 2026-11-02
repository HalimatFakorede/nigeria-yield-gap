"""Checks on the processed output. Run with: pytest -q"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (C.PROCESSED / "crop_panel.csv").exists(),
    reason="run the notebooks first",
)


@pytest.fixture(scope="module")
def panel():
    return pd.read_csv(C.PROCESSED / "crop_panel.csv")


@pytest.fixture(scope="module")
def dec():
    return pd.read_csv(C.PROCESSED / "decomposition.csv")


@pytest.fixture(scope="module")
def gap():
    return pd.read_csv(C.PROCESSED / "yield_gap.csv")


@pytest.fixture(scope="module")
def headline():
    return json.load(open(C.PROCESSED / "headline.json"))


# --- the panel

def test_scope(panel):
    assert set(panel["crop"]) == set(C.CROPS.values())
    assert panel["country"].nunique() == len(C.PEERS)


def test_no_blanks(panel):
    assert panel.isna().sum().sum() == 0


def test_yields_are_possible(panel):
    assert panel["yield_t_ha"].between(*C.YIELD_BOUNDS).all()


def test_yield_equals_production_over_area(panel):
    assert np.allclose(panel["production_t"] / panel["area_ha"],
                       panel["yield_t_ha"], rtol=1e-9)


def test_no_duplicates(panel):
    assert not panel.duplicated(["country", "crop", "year"]).any()


def test_encoding_survived(panel):
    assert "Côte d'Ivoire" in set(panel["country"])
    assert not any("Ã" in c for c in panel["country"].unique())


def test_nigeria_has_every_year(panel):
    ng = panel[(panel["country"] == "Nigeria")
               & panel["year"].between(C.START_YEAR, C.END_YEAR)]
    assert len(ng) == len(C.CROPS) * (C.END_YEAR - C.START_YEAR + 1)


# --- the decomposition

def test_log_split_is_exact(dec):
    assert (dec["ln_area"] + dec["ln_yield"] - dec["ln_prod"]).abs().max() < 1e-12


def test_weights_add_to_one(dec):
    assert abs(dec["weight"].sum() - 1) < 1e-12


def test_shares_add_to_100(headline):
    assert abs(headline["share_from_area_pct"]
               + headline["share_from_yield_pct"] - 100) < 0.1


def test_log_answer_sits_between_the_two_orders(headline):
    n = headline["naive_split"]
    lo = min(n["land_applied_first_pct"], n["yield_applied_first_pct"])
    hi = max(n["land_applied_first_pct"], n["yield_applied_first_pct"])
    assert lo < headline["share_from_area_pct"] < hi


def test_growth_came_from_land(headline):
    assert headline["production_growth_pct"] > 100
    assert headline["share_from_area_pct"] > 100
    assert headline["share_from_yield_pct"] < 0


# --- the yield gap

def test_every_peer_is_big_enough(gap, panel):
    ref = panel[panel["year"].between(*C.REF_WINDOW)]
    area = ref.groupby(["country", "crop"])["area_ha"].mean()
    for row in gap.itertuples():
        assert area.loc[(row.best_country, row.crop)] >= \
            C.MIN_PEER_AREA_SHARE * row.nigeria_area_ha


def test_nigeria_is_not_its_own_peer(gap):
    assert "Nigeria" not in set(gap["best_country"])


def test_upside_matches_the_yield_difference(gap):
    assert np.allclose(gap["nigeria_area_ha"] * (gap["best_t_ha"] - gap["nigeria_t_ha"]),
                       gap["upside_t"], rtol=1e-9)


def test_cassava_is_most_of_the_gap(headline):
    assert headline["yield_gap"]["cassava_share_of_upside_pct"] > 50


# --- the models

def test_fixed_effects_shrink_the_plain_answer():
    m = json.load(open(C.PROCESSED / "model_results.json"))
    assert m["elasticity"] < m["elasticity_country_fe_only"] < m["elasticity_no_fixed_effects"]
    assert m["ci95"][0] > 0


def test_ml_was_compared_to_a_strong_baseline():
    ml = json.load(open(C.PROCESSED / "ml_results.json"))
    assert ml["r2_random_split_no_lag"] > ml["r2_time_split_no_lag"]
    assert ml["r2_best_baseline"] > ml["r2_time_split_no_lag"]
