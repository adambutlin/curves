# The 2026 bond selloff through both frozen models

> **Update (5 October 2026).** The cross-Atlantic numbers below come from the free-data
> model, whose euro-area prices close before US prices. The synchronised model
> ([12-brandt-synchronised-results.md](12-brandt-synchronised-results.md)) corrects the
> euro-area part: the euro-area monetary contribution falls from +21bp to +3bp over the
> selloff window, and US news accounts for essentially all of the euro-area 10-year rate's
> rise in 2026. The US-model results are unaffected.

*Both models frozen at end-2025 (US model: commit `3cf38c2`, SHA-256 `cafa5f25...e7b8`;
cross-Atlantic model: commit `897dea3`, SHA-256 `2fd02b43...e345ae`), fingerprints
checked before use; no parameter re-estimated on 2026 data. Protocol: pre-registration
08, Section 5. Data: US model to 31 August 2026 (the latest CRSP month), cross-Atlantic
model to 25 September 2026. Tables: `reports/structural_propagation/application_2026/`;
figures 9-11.*

---

## Conclusion

1. **The selloff was led by US news, and the Bund's share of it was largely imported.**
   In the cross-Atlantic model, US monetary and macro news account for about 60% of the
   rise in both the 10-year Treasury and the 10-year Bund over 27 February-19 August;
   euro-area monetary news adds over a third of the Bund's rise.
2. **At the front end the selloff was a repricing of the expected course of US policy
   rates.** Growth and monetary news explain 98% of the 2-year's rise in 2026 to date
   (82% over the selloff window), and over 2026 to date both contributions are positive
   across the identified set.
3. **What drove the 10-year Treasury beyond the front end is model-dependent.** The US
   model reads much of it as premium shocks, in particular a fall in Treasuries' value
   as an equity hedge. The NY Fed's term-structure model reads it mostly as expected
   rates. The identified sets are wide enough to accommodate both.
4. **The frozen models' propagation relationships were neither confirmed nor refuted by
   2026**, as the power calculation predicted: about 150-180 trading days are too few.

## 1. Decompositions

Historical decomposition through each VAR's dynamics: each day's contribution of
shock $k$ is $\sum_{s \le 20} w'\Psi_s B_{\cdot k}\,\varepsilon_{t-s,k}$, where $\Psi_s$
are the VAR's moving-average weights, $B$ the impact matrix and $w$ selects the yield.
For the cross-Atlantic model this credits the Bund's next-day catch-up to the US shock
that caused it. Medians are the median-target model; brackets are 90% of the identified
set. "Other" is the effect of intercepts and older shocks.

**27 February to 19 August 2026**

| | Actual | Contributions (bp) |
|---|---|---|
| Treasury 10y, US model | +68 | growth +21 [1, 58], monetary +9 [-1, 36], common premium +15 [-6, 43], hedging premium +29 [2, 61], other -7 |
| Treasury 2y, US model | +74 | growth +38 [8, 72], monetary +22 [-2, 52], common premium +7 [-1, 25], hedging premium +17 [0, 45], other -10 |
| Treasury 10y, cross-Atlantic | +68 | US monetary +21 [-10, 46], US macro +21 [0, 62], global risk +14 [-1, 55], euro-area macro +11 [-6, 31], euro-area monetary 0, other +1 |
| Bund 10y, cross-Atlantic | +57 | euro-area monetary +21 [-5, 29], US monetary +18 [-6, 40], US macro +18 [-1, 54], global risk +8 [-1, 41], euro-area macro -2, other -6 |

**2026 to date** (Treasury 2y and 10y to 31 August; Bund to 25 September)

| | Actual | Contributions (bp) |
|---|---|---|
| Treasury 2y, US model | +79 | growth +35 [7, 73], monetary +42 [7, 69], premia +16, other -14 |
| Treasury 10y, cross-Atlantic | +95 | US monetary +49 [0, 64], US macro +24 [2, 69], global risk +16 [0, 70], euro area +6 |
| Bund 10y, cross-Atlantic | +69 | US monetary +39 [0, 55], US macro +20 [0, 60], euro-area monetary +12 [-6, 27], global risk +9, other -9 |

**Reading the signs.** A positive global-risk contribution means risk sentiment
*improved* over the window: the safe-haven bid for Treasuries and Bunds faded and their
yields rose. Euro-area monetary news pulled Bund yields down by about 19bp to the end of
February and then pushed them up by about 21bp over the selloff window.

**Front end versus long end.** In the US model, growth and monetary news flattened the
2s10s curve (over 2026 to date both contributions to the slope are negative across the
identified set), while the premium shocks steepened it. The selloff was a bear flattening driven by policy
expectations with a partly offsetting long-end premium move.

## 2. The disagreement on the 10-year Treasury

Over the same window the NY Fed's published term-structure model attributes about
+51bp of the 10-year's rise to expected rates and +17bp to the term premium. The US
model attributes +30bp to expectations shocks (growth and monetary) and +45bp to premium
shocks. The two are not the same object:

- the NY Fed model splits the *level* of yields into a model-implied expected short-rate
  path and a residual premium, using monthly cross-sectional pricing;
- the US model labels *daily moves* by their co-movement with equities and their pattern
  across maturities. A day on which the 10-year rises with equities and by more than the
  2-year is read as a fall in Treasuries' hedging value, whatever the forward path did.

The US model's own bands also allow most of the move to be expectations news (growth
alone is admissible up to +58bp). The robust statement is narrower: the front end moved
on policy-rate news, and the long end's extra move came on days when bonds and stocks
behaved as they do when bonds stop hedging equity risk.

## 3. Propagation in 2026

Forecasts of 2026 outcomes from regressions estimated on data through 2025:

- **US model.** No model beats a no-change forecast of the 2-year; for the 10-year the
  curve-state models are slightly positive at 5 and 20 days (+0.7% and +0.9% $R^2$), the
  structural split adds nothing significant.
- **Cross-Atlantic model, close-to-close.** The Bund's next-day catch-up again "predicts"
  a quarter to a third of its one-day moves out of sample (+26% to +35% $R^2$),
  confirming that the timing artefact is a stable feature of the recorded data.
- **Cross-Atlantic model, from the next close.** Small positive $R^2$ for the Bund at 10
  and 20 days (+2.5%), consistent with momentum in a selloff year; the origin split
  improves on the curve-state model at 20 days (Clark-West p = 0.02), one horizon in
  one short year.

As anticipated in the design note, 2026 can validate decompositions but cannot test
propagation: these results neither support nor contradict the 1983-2025 conclusion.
