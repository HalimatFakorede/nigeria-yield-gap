# Nigeria Crop Growth and Yield Analysis

**Has growth in Nigeria's crop production come from harvesting more area, improving yields, or both?**

I analyzed production, harvested area, and yield for eight crops in Nigeria. I wanted to understand how these measures changed over time, compare Nigeria's yields with those of selected African countries, and examine the relationship between fertilizer use and cereal yields.

[Open the dashboard](https://nigeria-yield-gap.streamlit.app/)

## The questions

1. How did harvested area and yield change for each crop?
2. How much did changes in area and yield contribute to a weighted index of production growth?
3. How do Nigerian yields compare with those of selected countries that grow the same crops?
4. What relationship appears between fertilizer use and cereal yields in country-level data?
5. Does a machine-learning model improve on a simple yield benchmark?

## What I found

### Area and yield did not change in the same way for every crop

The analysis compares averages for 1990-1992 and 2021-2023. Maize yield increased by approximately 84%, while its harvested area increased by about 14%. Other crops followed different patterns; the dashboard shows both changes for each crop.

For the eight crops together, I used a weighted index to separate changes in production into area and yield components. In the saved results, the area component represented 128.4% of the net change in the weighted log index, while the yield component represented −28.4%. The area contribution can be greater than 100% because the negative yield contribution offsets part of it. These percentages refer to the index, not the share of additional tonnes produced.

This is a breakdown of observed changes, not proof that expanding harvested area caused production to grow. The index is also not the same as the percentage change in total tonnes produced. The method is explained below.

### Nigeria's position depends on the crop and comparison group

For 2019-2023, Nigeria's average yield was above the median of the qualifying comparison countries for six of the eight crops. The countries in each comparison vary because a country had to grow at least 10% of Nigeria's harvested area for that crop to qualify. Some groups are small; the yam comparison has one qualifying peer.

For cassava, the saved data shows average yields of about 5.9 tonnes per hectare in Nigeria and 23.7 tonnes per hectare in Ghana. This is a comparison, not an estimate of what Nigeria could achieve: farming conditions, data quality, and other factors differ.

### The model was only slightly ahead of a simple benchmark

I compared a gradient boosting model with a baseline that uses each country's last recorded yield before the test period. In a rerun using the saved modeling data, the model achieved an R² of 0.8867, compared with 0.8823 for the baseline. Both scores were calculated on log cereal yield; the difference is small.

The model uses some inputs from the same year as the yield being assessed. I have not established whether those inputs would be available when a prediction is needed, so this is a retrospective comparison—not a validated real-time forecast.

## How I analyzed the data

### Production, area, and yield

For each crop:
**Production = harvested area × yield per hectare**

I calculated the average harvested area and average yield for the first and last three-year periods. I then used the changes in those averages to examine the area and yield components of production growth.

To bring the eight crops together, the notebook gives each crop a weight based on its share of production at the start and end of the period. It uses logarithms to combine the crop-level changes. The result is a weighted production index, not a direct calculation of the change in total production tonnes.

The notebook multiplies average area by average yield to form the endpoint values. This is not always the same as calculating average annual production. The analysis does not establish whether an increase in harvested area involved newly cleared land.

### Peer-country comparison

I compared Nigeria's average yield for each crop with selected African countries over 2019-2023. To avoid comparing Nigeria with countries growing a very small amount of a crop, I included a peer only when its average harvested area met the 10% threshold described above. The choice of countries and threshold affects the results.

### Fertilizer and cereal yields

I used World Bank country-level data to examine the relationship between fertilizer use and cereal yields. The analysis includes country and year fixed effects and controls for cereal area and rural population share. The saved model uses 9,466 observations from 178 countries.

This is an observational analysis. It can show a relationship in the data, but it does not establish that fertilizer use caused yields to change. Fertilizer is measured per hectare of arable land, while the yield measure covers cereals; both are national-level measures.

### Machine-learning comparison

I trained the model on data from before 2013 and tested it on 2013–2024. The baseline holds each country's yield at its last available value before the test period. For the test rows, the model also receives that pre-test yield as an input.

The small score difference should not be treated as proof that the model will perform better in practice. The same-year input limitation above matters, and additional time-based tests would be needed.

## Data

| Source | Used for |
|---|---|
| FAOSTAT Crops and Livestock Products | Crop production and harvested area |
| World Bank World Development Indicators | Population, fertilizer use, cereal yield, and other country indicators |

The eight crops are **maize, rice, cassava, sorghum, millet, yam, cowpea, and groundnut**. The crop comparison covers Nigeria and selected African countries. The fertilizer model uses a separate international dataset.

See [`data/raw/SOURCES.md`](data/raw/SOURCES.md) for data links and indicator codes. Some observations are estimated or imputed rather than directly measured, and source data can be revised.

## Limits

- The analysis covers eight crops and uses national averages. It does not describe every farm or all food production in Nigeria.
- Combined production per person in the notebooks is not a measure of food consumption, nutrition, or food security. The crops differ in composition and edible content.
- Peer groups differ by crop, and high yields in another country are not automatically achievable in Nigeria.
- The fertilizer results are associations, not evidence of cause and effect.
- Model scores can vary with source data and software versions.
- The project was rebuilt from downloaded FAOSTAT and World Bank data, and the existing tests passed. The tests check parts of the outputs; they do not prove every result is correct.

## Run the dashboard on Windows

From the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard reads the saved files in `data/processed/`.

## Rerun the analysis

Install the development requirements with `python -m pip install -r requirements-dev.txt`, then run the notebooks in order from the `notebooks` folder. They download data from FAOSTAT and the World Bank when needed. Source revisions may change the results, so keep a backup of the saved outputs before rerunning.

The rebuild reported above used Python 3.13.18, scikit-learn 1.6.1, pandas 2.2.3, and NumPy 2.3.5. Results may differ across software versions.

To run the existing checks:

```powershell
python -m pytest -q
```

## Project files

- `app.py`- Streamlit dashboard
- `notebooks/`- data preparation, analysis, modeling, and charts
- `src/`- settings and data-loading code
- `data/processed/`- saved analysis results
- `tests/`- checks on saved outputs
- `NOTES.md`- development notes

---

**Halimat H. Fakorede** · [LinkedIn](https://linkedin.com/in/halimatfakorede) · [Email](mailto:fakoredehalimat1@gmail.com)
