# Raw data

Nothing in this folder is committed. The notebooks download what they need on the first
run and keep it here.

## FAOSTAT

Downloaded by `src/io_utils.download_faostat()`.

| File | Archive |
|---|---|
| Production Crops and Livestock, Africa | `Production_Crops_Livestock_E_Africa.zip` |
| Inputs Fertilizers by Nutrient, Africa | `Inputs_FertilizersNutrient_E_Africa.zip` |

From `https://bulks-faostat.fao.org/production/{name}.zip`

I use the Africa file rather than the global one. I need the neighbouring countries for
the comparison, and the global file is far bigger for nothing extra.

Covers 1961 to 2024, 57 countries, 273 items.

These files are utf-8. latin-1 reads them without any error but turns `Côte d'Ivoire`
into `CÃ´te d'Ivoire`, so `load_faostat` checks for that and stops.

Every value is flagged: `A` official, `E` estimated, `I` imputed, `X` from another
organisation. A lot of the Nigerian numbers are estimates.

## World Bank

From the public API, no key needed.

| Indicator | Code |
|---|---|
| Population | `SP.POP.TOTL` |
| Fertilizer, kg per ha of arable land | `AG.CON.FERT.ZS` |
| Cereal yield, kg per ha | `AG.YLD.CREL.KG` |
| Land under cereals, ha | `AG.LND.CREL.HA` |
| Rural population, % | `SP.RUR.TOTL.ZS` |

The indicator endpoints mix regions and income groups in with countries, and filtering on
the length of the code does not remove them because `WLD` is three letters.
`real_country_codes()` uses the World Bank's own country list instead.

## Rebuild record

All six notebooks were executed in order using the FAOSTAT Africa crop-production download and live World Bank WDI responses. The downloaded FAOSTAT CSV used for this rebuild had SHA-256 `ce8fb84f11b6d38f6a3dcfc2162a4fc2de2c4b481a158cc21b438dd609b516af`. The resulting saved `model_frame.csv` has SHA-256 `423d1f797f9e0f2f3682cad6239e3062f88e4540ea0526df151aab4bc06da473`. World Bank API responses were not archived separately. Sources can be revised, so future fresh downloads may differ.
