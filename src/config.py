"""Settings used across the notebooks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "outputs" / "figures"

for _d in (RAW, PROCESSED, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)


# FAOSTAT name -> short name
CROPS = {
    "Maize (corn)":                  "Maize",
    "Rice":                          "Rice",
    "Cassava, fresh":                "Cassava",
    "Sorghum":                       "Sorghum",
    "Millet":                        "Millet",
    "Yams":                          "Yam",
    "Cow peas, dry":                 "Cowpea",
    "Groundnuts, excluding shelled": "Groundnut",
}

PEERS = [
    "Nigeria",
    "Ghana", "Benin", "Cameroon", "Niger",
    "Mali", "Burkina Faso", "Senegal", "Côte d'Ivoire",
    "Ethiopia", "Kenya", "Uganda", "United Republic of Tanzania",
    "Egypt", "South Africa",
]

PEER_GROUPS = {
    "Neighbours":        ["Ghana", "Benin", "Cameroon", "Niger"],
    "West Africa":       ["Mali", "Burkina Faso", "Senegal", "Côte d'Ivoire"],
    "East Africa":       ["Ethiopia", "Kenya", "Uganda", "United Republic of Tanzania"],
    "Irrigated or commercial": ["Egypt", "South Africa"],
}

# FAOSTAT and the World Bank spell three of these differently
WB_NAME_FIX = {
    "Egypt, Arab Rep.": "Egypt",
    "Tanzania":         "United Republic of Tanzania",
    "Cote d'Ivoire":    "Côte d'Ivoire",
}

START_YEAR = 1990
END_YEAR = 2023
ENDPOINT_WINDOW = 3          # years averaged at each end
REF_WINDOW = (2019, 2023)    # window for comparing yields

MIN_PEER_AREA_SHARE = 0.10   # a peer must farm at least this much of Nigeria's area
YIELD_BOUNDS = (0.05, 100.0) # tonnes per hectare these crops can actually reach
MIN_YEARS_PER_COUNTRY = 15   # fixed effects need a run of years to work with

ML_SPLIT_YEAR = 2013
RANDOM_SEED = 0

FAOSTAT_BULK = "https://bulks-faostat.fao.org/production/{name}.zip"
FAOSTAT_FILES = {
    "production": "Production_Crops_Livestock_E_Africa",
    "fertilizer": "Inputs_FertilizersNutrient_E_Africa",
}

WDI_INDICATORS = {
    "SP.POP.TOTL":    "population",
    "AG.CON.FERT.ZS": "fert_kg_ha",
    "AG.YLD.CREL.KG": "cereal_yield_kg_ha",
    "AG.LND.CREL.HA": "cereal_area_ha",
    "SP.RUR.TOTL.ZS": "rural_pop_pct",
}

GREEN, GOLD, CLAY, INK, GREY = "#1f6b45", "#c8892c", "#a8543a", "#0d1b14", "#8a958e"

PLOT_STYLE = {
    "figure.dpi": 120, "savefig.dpi": 160, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlepad": 12,
    "figure.facecolor": "white", "axes.facecolor": "white",
}
