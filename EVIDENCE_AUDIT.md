# Evidence audit: the 2026 Treasury selloff note

Which files are authoritative, what was recomputed for the note, which discrepancies were found and how they were resolved, and where every headline number comes from. Audit date: 7 October 2026.

## 1. Authoritative model and results

The note uses one model: the synchronised cross-Atlantic model ("Model A") with the Treasury curve attached by projection. Earlier models in the repository (the Cieslak–Pang US model, the free-data cross-Atlantic model, the UK–US models) are not used.

| Item | File | Fingerprint | Commit |
|---|---|---|---|
| Pre-registration, model and 2026 protocol | `docs/research/structural-propagation/08-…`, `11-brandt-synchronised-preregistration.md` | | `26bd4d4`, `a88caf7` |
| Frozen model, end-2025 | `reports/structural_propagation/brandt_sync/model_brandt_sync_end2025.npz` | SHA-256 `4b204619…d489` | `ee532fe` |
| Pre-registration, Treasury curve | `docs/research/structural-propagation/15-us-curve-preregistration.md` | | `dad0e57` |
| Frozen Treasury-curve loadings | `reports/structural_propagation/us_curve/loadings_end2025.npz` | SHA-256 `3015f33c…7158` | `881e10e` |
| 2026 application as committed | `reports/structural_propagation/us_curve/` (`decomposition_windows.csv`, `monthly_leaders.csv`, `regimes.csv`, `signatures.csv`, `apply_summary.json`, `freeze_summary.json`, `forecast_summary.csv`) | | `4896388` |
| Write-up of that application | `docs/research/structural-propagation/16-us-curve-results.md` | | `4896388` |
| Replication record | `reports/structural_propagation/brandt_sync/summary.json`, `event_study.csv` | | `ee532fe` |

Both frozen files were re-hashed during the audit and match. They contain posterior parameter draws only (A, B, Σ and the loadings θ), no data.

## 2. Specification as implemented

| | |
|---|---|
| Variables | 10-year euro-area OIS (EONIA composite to 2019, €STR from 2 January 2020, spliced in levels); Euro Stoxx 50 future, roll-adjusted; S&P 500; euro-dollar; euro-area minus US 10-year spread (US leg: LSEG 10-year benchmark). All at or near the New York close |
| Sample, lags, prior | 3 January 2007 to 30 December 2025 (4,673 days); 4 lags; Minnesota prior, tightness 0.2, conjugate normal-inverse-Wishart posterior |
| Identification | Brandt et al. Table 1 sign restrictions on impact (`brandt.restriction_matrix`); uniform rotations drawn jointly with the reduced form, 500 per draw; 1,000 admissible draws (2.5% acceptance) |
| Shocks | euro-area monetary, euro-area macro, US monetary, US macro, global risk (positive = risk-off) |
| Treasury maturities | H.15 2-, 5-, 10-, 30-year yields projected on the shocks at lags 0–2, by OLS, draw by draw, on 2007–2025; NY Fed ACM daily fitted yield, expected rates and term premium at 2, 5 and 10 years likewise |
| Representative model | median-target draw (Fry–Pagan), draw 992 |
| 2026 data | 188 model days to 5 October 2026; the first change is measured from the close of 30 December 2025 |

## 3. What was recomputed for the note

No estimation was rerun. `scripts/build_research_output.py` re-applies the frozen model and loadings, draw by draw, to the cached data through 5 October 2026. Before writing anything it checks that the median-target model reproduces the committed 2026 totals: the largest gap across the 2-, 5-, 10- and 30-year yields and the ACM 10-year series, in both committed windows, is 0.0000bp. It then records what the committed tables lacked: medians, 5–95% ranges and probabilities across all 1,000 admissible models (`output/data/`). Curve signatures, fit and forecasting tables are reshaped from committed files without recomputation.

## 4. Discrepancies and how they were resolved

1. **Dating of the 2026 window (labelling error, numbers unaffected).** The committed "2026 to date" totals start at the close of 30 December 2025, not 31 December: Eurex, where the euro-area equity future trades, was shut on 31 December, so the model's last 2025 day is 30 December and 31 December's moves fall into its first 2026 day. The 10-year's +117bp is measured from 4.14% on 30 December; from the 31 December close it is +113bp (2-year +137bp, 5-year +133bp, 30-year +82bp). The note labels every window from the 30 December close.
2. **Representative model against the identified set (presentation issue).** Document 16 reports median-target values as point estimates: US news 96bp of the 10-year's rise, "euro-area news for nothing", 82% of the rise from US news. Across the 1,000 admissible models the median-target model sits at the 77th percentile of the US-news contribution and the 2nd percentile of the euro-area contribution. Medians across the set: US news 76bp (31–119), global risk 24bp (−2 to 74), euro area 11bp (−1 to 47). The note leads with the medians and ranges, keeps the median-target model for the additive figures, and does not claim that euro-area news contributed nothing.
3. **Leadership of the driver over time.** Document 16's rolling 20-day leaders (US monetary news 22 June–9 July, global risk 4–25 August) describe the median-target model only; the document itself notes that the leader within US news agrees across only 20–60% of models. The note reports leadership by calendar month with the share of models agreeing, and claims only what holds at the level of origin.
4. **Earlier 2026 numbers elsewhere.** Document 10 used the free-data model, whose European prices close five and a half hours early; document 12 shows that this misreads the overnight catch-up as euro-area news. Document 12 decomposes the LSEG 10-year benchmark through the VAR (+118bp; US macro 69, monetary 31) rather than H.15 yields by projection (+117bp; 67 and 29). Same conclusion; the note uses document 16's specification only.
5. **Checked and confirmed.** Document 16's claim that the 2s10s flattening is entirely unspanned front-end news holds across the set: the cross-asset contribution to 2s10s is positive in all 1,000 models (median +41bp, minimum +27bp), and each US and global shock steepens the curve in 83–100% of models.

Figures 18–22 in `reports/structural_propagation/` remain the record of the committed run. `output/figures/` uses the same model and adds the cross-model uncertainty.

## 5. Where the headline numbers come from

All values are in `output/data/headline_numbers.json`, computed from the tables below; the research page substitutes them programmatically.

| Number | Value | Source (`output/data/`) |
|---|---|---|
| 10-year and 2-year rise | +117bp, +139bp | `decomposition_2026.csv`, `actual_bp` (H.15) |
| Rise from the 31 December close | +113bp | `market_context_2026.csv` |
| US news, 10-year: median, 5–95% | 76bp, 31–119bp | `decomposition_2026.csv`, `us_news_p50/p05/p95` |
| US news largest origin | 80% (10y), 88% (2y) | `p_us_largest` |
| US news more than half of the 10-year's rise | 72% of models | `p_us_more_than_half` |
| Unspanned, 2-year | 61bp (44–80) | `unspanned_p50/p05/p95` |
| 2s10s: cross-asset, unspanned | +41 (31–50), −63 (−72 to −53) | rows `2s10s`, `all_shocks_*`, `unspanned_*` |
| US macro exceeds US monetary | 53% (10y) | `p_macro_gt_monetary` |
| Monthly legs and leadership | +33, +31, +54bp; 87%, 65%, 86% | `monthly_2026.csv` |
| ACM: 2-year expected rates, unspanned part | +99bp, 66bp (59–74) | `acm_comparison_2026.csv` |
| ACM: 10-year expected rates, term premium | +86bp, +23bp | `acm_comparison_2026.csv` |
| Steepening share by shock | 83–100% | `curve_signatures.csv`, `p_steepens_2s10s` |
| Daily R², in sample and 2026 | 52/81/91/80%, 59/83/92/80% | `explanatory_fit.csv` (from `freeze_summary.json`, `apply_summary.json`) |
| Forecasting | Clark–West p ≥ 0.11; no model beats no change | `forecast_oos.csv` (from `forecast_summary.csv`) |
| Same-close artefact | R² +1.3%, p < 0.001 | `forecast_oos.csv`, 10y, same close |
| Replication | 35% vs 40%; 15 of 18 events, 50% on average | `model_record.json` |
| S&P 500 over the window | +13% | `market_context_2026.csv` |

## 6. Forecasting evidence

From `scripts/run_us_curve.py forecast` (committed in `4896388`). Real time, 2012–2025: the VAR, identification (200 draws) and loadings re-estimated each year on earlier data; outcomes are changes over 1, 5 and 20 days starting at the next close. Models: no change; own move; plus curve state; plus the US, euro-area and global parts of the day's move (the structural model); plus all five VAR innovations (identification-free). Every out-of-sample R² against no change is negative in 2012–2025, and adding the origin never improves on the curve-state model (Clark–West p from 0.11 to 1.00). In 2026, with the frozen model, no specification improves on no change by more than 0.2% of variance. The one positive result, from the same close at the 10-year, comes from H.15 yields being recorded before the New York close and is not tradeable.

## 7. Licensed data and repository hygiene

- LSEG prices are cached in `data/raw/` and git-ignored. Every commit on the branch since the remote's first commit was scanned: no file under `data/raw/` other than `.gitkeep`, no credentials or keys, no local absolute paths.
- LSEG-derived daily series by shock stay in git-ignored `lseg_private/` folders.
- The published tables give daily values only for the 10-year and only by origin group (US news, global risk, euro area, unspanned) and as cross-model quantiles; other maturities appear only as window and monthly totals. Three daily group series cannot identify the five daily shocks, so the licensed series cannot be reconstructed from the published tables and the committed model.
- The S&P 500 is from Yahoo Finance and is not redistributed; one summary change is reported.

## 8. Not verified here

The LSEG cache dates from 6 October 2026 and the H.15 download from 7 October 2026; a later re-download could revise history. The reproduction check in the build fails loudly if the data no longer reproduce the committed results. Bibliographic details of the references were not checked against the publishers.
