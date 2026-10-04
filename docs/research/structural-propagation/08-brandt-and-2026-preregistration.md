# Pre-registration: the cross-Atlantic model and the 2026 application

*Written on 4 October 2026, after the owner approved (i) building the Brandt et al.
model alongside the frozen US model and (ii) opening the 2026 holdout for both. Written
before the cross-Atlantic model is estimated and before any 2026 data are passed through
either model. The US model was frozen in commit `3cf38c2` (SHA-256 of the model file
`cafa5f25...e7b8`). Deviations go in Section 7.*

## 1. The cross-Atlantic model

Brandt, Saint Guilhem, Schröder and Van Robays (2021, ECB Working Paper 2560): a daily
Bayesian VAR in five variables with five sign-identified shocks (euro-area monetary,
euro-area macro, US monetary, US macro, global risk), conjugate normal-inverse-Wishart
prior, uniform prior over rotations, Arias, Rubio-Ramírez and Waggoner (2018)
Algorithm 1, four lags, 1999-2023. Restrictions exactly as their Table 1 (reproduced in
the model's documentation). The spread restriction identifies the country of origin: a
domestic shock moves the domestic long rate by more than the foreign one.

| Their variable | Here (free data) | Why |
|---|---|---|
| Euro-area 10-year OIS | Bundesbank 10-year Svensson zero Bund yield | They report the Bund gives similar results (footnote 8); no free OIS history |
| Euro Stoxx (broad) price index | Euro Stoxx 50 from April 2007, average DAX/CAC 40 return before | No free daily Euro Stoxx history before 2007; the proxy's daily return correlation with the Euro Stoxx 50 is 0.985 (2007-2025) |
| S&P 500 | S&P 500 (Yahoo) | Matches FRED's official series: return correlation 0.99999 |
| USD/EUR | FRED noon buying rate, dollars per euro | Free daily since 1999 |
| US 10-year Treasury | Gürkaynak-Sack-Wright 10-year zero | Same curve family (Svensson) as the Bund leg |

Sample 4 January 1999 to 31 December 2025 (theirs ends 2023; the 1999-2023 sub-sample is
also reported). Minnesota tightness 0.2, as in the US model. 1,000 accepted draws, seed
20261008. Robustness: the post-April-2007 sample, in which the euro-area equity series is
the Euro Stoxx 50 throughout.

## 2. Replication checks (what "replicated" means)

1. **Spillover shares.** One-step-ahead variance shares (equal to impact shares in a
   VAR): Brandt et al. report that US shocks explain close to 40% of the variance of
   euro-area yields and equity prices, and euro-area shocks about 30% of US equity.
2. **Event study.** Their Table 2: 18 dated events with a prior on the dominant shock.
   For each, the two-day (event day and next day) change in the euro-area 10-year rate
   is decomposed by shock. A hit is an event whose largest absolute contribution comes
   from a shock in the prior set. Reported: the hit rate for the median-target model and
   the share of admissible draws scoring a hit, event by event.
3. **Global risk.** The global-risk shock should co-move positively with daily changes in
   VIX (FRED) and in the MOVE index of Treasury implied volatility (Yahoo, from 2002).

## 3. Propagation tests

Exactly the MVP's tests (pre-registration 02, Section 5), with the cross-Atlantic
outcomes and an origin split in place of the expectations/premium split:

- **Outcomes:** subsequent changes over 1, 5, 10 and 20 days in the euro-area 10-year
  rate (primary), the US 10-year rate and the euro-area minus US spread.
- **Controls:** both 10-year levels; for each, the change and the volatility over the
  previous 20 days.
- **Test A:** do the other four daily innovations predict the outcome beyond its own
  move and the controls (identification-free)?
- **Test B:** drift after each of the five shocks, across the identified set.
- **Test C:** split the outcome's daily innovation by origin: domestic, foreign and
  global. Regress on the own move plus the foreign and global parts; H0: both extra
  coefficients are zero. Placebo: 1,000 random rotations, shocks randomly grouped 2/2/1.
- **Real time:** expanding window, forecasts for 2004-2025, models M0-M4 as in the MVP
  (M3 adds the foreign and global parts, averaged over the identified set).

**Decision rules,** as in the MVP: origin matters for the euro-area 10-year if Test A
rejects at two or more horizons and the full-innovation model improves on M2 in real
time at those horizons. The identification carries information if the origin split
beats the placebo in a majority of draws at two or more horizons and M3 improves on M2
in real time at two or more horizons.

## 4. Freezing

The end-2025 cross-Atlantic model (VAR draws, impact matrices) is saved with its SHA-256
before any 2026 observation is loaded into either model.

## 5. The 2026 application

Both frozen models; no parameter, restriction or draw is re-estimated on 2026 data.

1. **Daily shocks for 2026** from the end-2025 VAR coefficients and impact matrices,
   draw by draw.
2. **Decompositions** of cumulative changes, with the median-target model for charts and
   5-95% bands across admissible draws:
   - US model: the 10-year and 2-year Treasury yields and the 2s10s slope;
   - cross-Atlantic model: the Bund and Treasury 10-year yields and their spread.
   Windows: 2026 to date, and 27 February to 19 August 2026, the window used in the
   August descriptive work (Section 6).
3. **Propagation in 2026:** forecasts of 2026 outcomes from predictive regressions
   estimated on data through 2025; out-of-sample $R^2$ against no change and Clark-West
   tests. About 160-190 trading days give low power (design note, Section 2.4): this is
   reported as a consistency check, not as a test of the hypothesis.

## 6. Disclosure

Already known about 2026 before this application (design note, Section 2.5): between
27 February and 19 August the US 10-year rose about 68bp (NY Fed published ACM: +51bp
expected rates, +17bp term premium), the Bund about 57bp, and sterling was flat. Both
models' restrictions were fixed long before that knowledge (2021 publications), and
neither model is re-estimated on 2026 data.

## 7. Deviations log

| Date | Change | Reason |
|---|---|---|
| 4 Oct 2026 | Added, beside the pre-registered close-to-close tests: propagation tests and real-time evaluation on changes that start at the next close; variance shares at two and five days; re-estimation on two-day and weekly changes; lead-lag regressions | The first estimates showed that euro-area prices, recorded about five and a half hours before US prices, catch up the next day with US afternoon news (next-day Bund on today's Treasury: 0.40, t = 36). Close-to-close results are reported but are not economically interpretable |
| 4 Oct 2026 | The 2026 decompositions run through each VAR's dynamics (20-day moving-average weights) rather than adding up same-day impacts only | Credits the Bund's next-day catch-up to the US shock that caused it; the same-day version would assign it to "other" |
| 4 Oct 2026 | US model's 2026 data end on 31 August | The CRSP-based equity series is published monthly with a lag |
