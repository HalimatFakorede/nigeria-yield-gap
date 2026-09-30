# Extending This to Farm-Level Data (LSMS-ISA)

This analysis uses national aggregates, which cannot answer household-level questions. The natural next step is the **World Bank LSMS-ISA Nigeria General Household Survey Panel**, plot-level data on thousands of Nigerian farms across multiple waves.

It is not included here because it requires a registered account, and I wanted this repository reproducible by anyone with one command. This is the path to add it.

---

## 1. Get the data (about 20 minutes)

1. Go to **microdata.worldbank.org**
2. Create a free account
3. Search **"Nigeria General Household Survey Panel"**, waves are available for 2010/11, 2012/13, 2015/16, 2018/19 and 2023/24
4. Request access: state your purpose ("independent research on smallholder productivity"). Approval is usually automatic or within a day.
5. Download the **agriculture** modules in Stata `.dta` format

## 2. The files that matter

Naming varies by wave, but the structure is consistent:

| File pattern | Contains |
|---|---|
| `sect11a_plantingw*` | Plot roster, plot size, tenure |
| `sect11d_plantingw*` | Fertilizer, herbicide, pesticide use and cost |
| `sect11e_plantingw*` | Labour, household and hired |
| `sect11f_harvestw*` | Harvest quantity by crop, unit, conversion |
| `secta_harvestw*` | Household roster and demographics |
| `nga_householdgeovars_*` | Geo-variables: rainfall, temperature, elevation, soil, distance to market |

## 3. The five hard parts (budget your time here, not on modelling)

**1. Unit conversion is the whole game.** Harvest is reported in local units, *mudu*, *tiya*, *congo*, baskets, bundles, heaps. Each wave ships a conversion file mapping these to kilogrammes, often varying by crop and by zone. Without it, yield is meaningless. This is the same problem as the unit normalization in Project 2, several times harder.

**2. Plot area.** Both farmer-reported and GPS-measured areas exist. They differ systematically, farmers over-report small plots. Use GPS where available, report how often you had to fall back, and check whether your results change.

**3. Merging across modules.** Keys are `hhid` plus `plotid` plus `cropid`, and they are not always consistent between planting and harvest visits. Merge diagnostics are mandatory: report match rates at each join.

**4. Panel linkage across waves.** Households split, move and attrit. There is a panel key but attrition is non-random, the households that drop out are not like those that stay.

**5. Intercropping.** Many Nigerian plots carry two or more crops. Attributing plot area to a single crop yield is a genuine methodological choice. Document whichever rule you use (area-share, full-area, or restrict to pure stands) and test sensitivity.

## 4. The analysis this unlocks

```python
# Yield response at farm level, with controls national data cannot provide
log(yield_kg_ha) ~ log(fertilizer_kg_ha) + improved_seed + labour_days_ha
                 + plot_size + soil_quality + rainfall + distance_to_market
                 + gender_of_plot_manager + education + household FE + wave FE
```

Questions this answers that the national analysis cannot:

- **What is the marginal return to a naira of fertilizer at farm level**, and how does it vary by farm size and agro-ecological zone?
- **Is there an inverse farm-size/productivity relationship** in Nigeria? (A classic development economics question.)
- **Do female plot managers get lower yields, and is it the manager or unequal input access?** This is a high-value question for every gender-focused agricultural programme.
- **Which households are persistently low-yield?** A classification model here directly serves targeting for extension and input support, and directly mirrors what One Acre Fund, Babban Gona and agri-lenders do internally.

## 5. Why this is worth doing

Add this and the project becomes really rare: a portfolio piece using Nigerian farm-level panel microdata, with the unit-conversion and merge work done properly. Very few applicants have that, and it is precisely the work IITA, One Acre Fund, IFPRI and CGIAR analysts do daily.

**Suggested framing when you publish it:** *"Estimated fertilizer and improved-seed yield response on N Nigerian smallholder plots using World Bank LSMS-ISA panel data, including local-unit conversion, GPS plot-area reconciliation and intercropping treatment; identified low-productivity household segments for extension targeting."*

## 6. Honest time estimate

- Access and download: half a day
- Unit conversion and cleaning: **3-5 days** (this is the real cost)
- Merging and panel construction: 2 days
- Analysis and modelling: 2 days
- Write-up and dashboard: 2 days

Roughly two focused weeks. Do not underestimate the cleaning, and when you interview on it, **the cleaning is the part worth talking about**, because it is the part most candidates have never done.
