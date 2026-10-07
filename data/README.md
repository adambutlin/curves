# Data

The research note on the 2026 Treasury selloff needs two kinds of input. Licensed market data never enter the repository; public data are re-downloaded on demand. What the repository does contain are frozen model parameters and the derived tables from which every figure and number in the note is rebuilt.

## Inputs

**Licensed: LSEG Workspace, cached in `data/raw/`, git-ignored, never committed.** These are the model's euro-area and benchmark prices, recorded at or near the New York close:

| Variable | LSEG instrument | Field |
|---|---|---|
| 10-year euro-area OIS rate | `EUREON10Y=` to 2019, `EUREST10Y=` from 2020 | bid/ask mid, mid price |
| Euro Stoxx 50 future (front and second contract, for rolls) | `STXEc1`, `STXEc2` | last trade |
| Euro-dollar exchange rate | `EUR=` | mid price |
| 10-year US Treasury benchmark (the US leg of the spread) | `US10YT=RR` | mid yield |

Downloading them requires a running Workspace desktop session and an app key in the environment variable `LSEG_APP_KEY`. The key is read from the environment only and is never written to disk. The loader is `src/giltcurve/ingest/lseg.py`; each series is cached as `data/raw/lseg_<instrument>.csv`.

**Public, downloaded on demand into `data/raw/` (also git-ignored, since they are re-fetchable):**

| Series | Source |
|---|---|
| S&P 500 | Yahoo Finance (`^GSPC`) |
| 2-, 5-, 10- and 30-year constant-maturity Treasury yields (H.15) | FRED: `DGS2`, `DGS5`, `DGS10`, `DGS30` |
| Daily ACM fitted yields, expected short rates and term premia | Federal Reserve Bank of New York, `ACMTermPremium.xls`, sheet `ACM Daily` |

## What the repository contains

- **Frozen model parameters**, `reports/structural_propagation/brandt_sync/model_brandt_sync_end2025.npz` and `reports/structural_propagation/us_curve/loadings_end2025.npz`: posterior draws of the VAR coefficients, impact matrices and Treasury-curve loadings, with their SHA-256 hashes recorded in the research documents. They contain no data.
- **Committed results of the 2026 application** in `reports/structural_propagation/us_curve/`: window and monthly totals, curve signatures, fit and forecasting summaries.
- **Derived tables for the note** in `output/data/`:

| File | Content |
|---|---|
| `decomposition_2026.csv` | Contributions by origin and shock to the 2-, 5-, 10- and 30-year yields and the 2s10s and 10s30s slopes, for the whole window and three sub-windows: median-target value, median and 5–95% across the 1,000 admissible models, and the share of models in which each origin is the largest |
| `us10y_daily_cumulative_2026.csv` | The 10-year only, day by day: cumulative contributions of US news, global risk sentiment, euro-area news and the unspanned part, with cross-model quantiles |
| `monthly_2026.csv` | Monthly contributions by origin at each maturity, with cross-model shares |
| `acm_comparison_2026.csv` | The NY Fed's expected-rate and term-premium changes, decomposed the same way |
| `curve_signatures.csv` | Each shock's loading by maturity (bp per one-standard-deviation shock) and how often it steepens the curve |
| `explanatory_fit.csv`, `forecast_oos.csv` | Explanatory R² of the frozen loadings; out-of-sample forecasting results |
| `market_context_2026.csv` | H.15 yield levels and the S&P 500 at the window's start and end |
| `model_record.json` | Replication record of the frozen model on 2007–2025 |
| `headline_numbers.json` | Every number quoted in the research note, as formatted text |

## Why the derived tables cannot be inverted back to the licensed data

With the committed model parameters, a complete daily history of the five structural shocks would let someone rebuild the daily changes of the licensed series. The tables are therefore aggregated so that this is impossible: daily values are published for one maturity only, and only for three origin groups (US news combines two shocks and euro-area news two more) plus the unspanned part, which reflects H.15 data. Three daily series cannot identify five daily shocks. All other maturities appear only as window or monthly totals, and cross-model quantiles are order statistics that identify no individual model's shocks. The per-shock daily series stay in git-ignored `lseg_private/` folders under `reports/`.

## Rebuilding

```bash
python scripts/build_research_output.py                 # with the LSEG cache: re-derive, then rebuild
python scripts/build_research_output.py --skip-extract  # without it: rebuild from output/data/
```

Without the licensed cache the command skips the first step automatically and rebuilds the figures and the research page from the committed tables. With it, the command first re-applies the frozen model, draw by draw, and stops if the result differs from the committed 2026 application by more than 0.05bp. That check guards against silent revisions to downloaded data. Estimation itself (`scripts/run_brandt.py --sync ois`, `scripts/run_us_curve.py freeze`) is separate and is not part of the rebuild.
