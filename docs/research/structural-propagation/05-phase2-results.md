# Phase 2 results: regime-dependent identification and propagation

*US Treasuries and equities, daily, 1983-2025; 2026 sealed. Estimated on 4 October 2026
under [04-phase2-regime-preregistration.md](04-phase2-regime-preregistration.md), which
was hashed before estimation (01:50 UTC, SHA-256 `2551f5e1...4cb5`). Provisional
pending the owner's choice between redesign and abandonment. Tables:
`reports/structural_propagation/phase2/`; figure: `fig6_phase2_regimes.png`.*

---

## Conclusion

1. **Identifying the shocks within each stock-bond regime is economically better and
   sharpens the structural signal where policy and inflation news dominate.** In the
   regime in which bonds and stocks fall together, the expectations/premium split of
   the 2s10s slope is now special in 26-39% of admissible identifications at 5-20 days,
   against at most 9% when the regimes are pooled.
2. **It still does not clear the pre-registered bar for the 10-year yield**: the split
   beats random splits in a majority of draws at no horizon in either regime, and the
   regime-specific structural state does not improve real-time 10-year forecasts
   (Clark-West p = 0.41-0.90). Under the Phase 2 decision rule, **the linear daily
   design fails for the 10-year in both its constant and its regime-dependent form.**
3. **The 2-year is the one place the structural state earns its keep in real time.**
   The regime-specific split improves on the curve-state model at every horizon
   (Clark-West p ≤ 0.02), and from five days on it beats the unrestricted model that uses
   all cross-asset news: the parsimonious state representation the proposal hoped for,
   but only at the front end, mostly in the hedge regime, and not enough to beat a
   no-change forecast.

---

## 1. Two regimes, two decompositions

The regime is the sign of the correlation between daily 10-year yield changes and
equity returns over the previous 250 trading days. **Hedge regime**: the correlation is
positive, so yields fall when stocks fall and Treasuries insure equity risk.
**Co-movement regime**: bond and stock prices fall together, as when inflation and
discount-rate news dominate.

| Share of days in the hedge regime | |
|---|---|
| 1984-1999 | 7% |
| 2000-2019 | 89% |
| 2020-2025 | 52% |
| 2022-2023 | 37% |

The classification recovers the history economists would expect: a co-movement regime
through the disinflation of the 1980s and 1990s, a hedge regime from 2000, and a return
to co-movement during the 2022-2023 inflation shock.

**Result: the equity decomposition flips with the regime; the yield decomposition does
not.**

| Share of equity variance | Growth | Monetary | Common premium | Hedging premium |
|---|---|---|---|---|
| Hedge regime | 31% | 8% | 7% | 38% |
| Co-movement regime | 10% | 10% | 50% | 10% |

When Treasuries hedge, equity risk is mostly flight to quality and growth news; when
bonds and stocks fall together, half of equity variance is a common discount-rate
premium. Yield variance shares are similar in both regimes, because the maturity
restrictions pin them down, except that monetary news explains more of the 10-year in
the co-movement regime (12% against 3%). Pooling the two regimes, as the MVP did, forces
one impact matrix onto both and blurs exactly the common/hedging distinction that the
propagation tests rely on.

## 2. Propagation by regime

The expectations/premium split is estimated separately in each regime:
$r_{t,t+h} = \alpha + \theta_{EH} C^{EH}_t + \theta_{TP} C^{TP}_t + \delta' Z_t + e_{t+h}$,
with $C^{EH}_t$ and $C^{TP}_t$ the parts of the day-$t$ innovation due to
short-rate-expectations shocks and to premium shocks, built from that regime's impact
matrix.

**Result: in the co-movement regime the asymmetry is large and robust in sign.**

| Co-movement regime, 2s10s slope | h = 1 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| $\theta_{EH}$ (median) | 0.07 | 0.05 | 0.21 | 0.34 |
| $\theta_{TP}$ (median) | -0.05 | -0.15 | -0.15 | -0.22 |
| Share of draws with $\theta_{TP} < \theta_{EH}$ | 99% | 100% | 100% | 100% |
| Share of draws beating 90% of random splits | 10% | 39% | 26% | 34% |

When bonds and stocks fall together, a steepening driven by news about policy rates
continues, by a third over the following month, while a steepening driven by premium
shocks reverses, by about a fifth. The 10-year in the same regime shows the same sign
(the expectations-driven part continues by 14% the next day and 24% over a month,
against 4% and 7% for the premium-driven part), but the split beats random splits only
at one day (44% of draws).

In the hedge regime the pattern is different: at the 2-year, premium-driven moves
reverse (by 8-19% of the move within one to ten days, in 94-97% of draws) while
expectations-driven moves barely continue. Flight-to-quality rallies at the front end
partly unwind. For the 10-year in this regime the split has no predictive content.

**Pre-registered criterion (i)** asks for a majority of draws beating the placebo at two
or more horizons for the 10-year in at least one regime. The best case is 44% at one
horizon. **It fails.**

## 3. Real time, 2000-2025

Both impact matrices are re-estimated every year-end on training days of their regime,
with the regime itself measured in real time.

**Result: no gain for the 10-year; a consistent gain for the 2-year.**

| Real-time $R^2$ gain over the curve-state model | h = 1 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| 10-year, regime-specific split | -0.11pp (p = 0.60) | -0.09pp (0.41) | -0.05pp (0.46) | -0.11pp (0.90) |
| 2-year, regime-specific split | +0.52pp (p < 0.001) | +0.27pp (< 0.001) | +0.11pp (0.008) | +0.06pp (0.019) |
| 2-year, all cross-asset news by regime | +0.65pp (< 0.001) | -0.01pp (< 0.001) | -0.28pp (0.04) | -0.16pp (0.005) |

*p-values are Clark-West tests against the curve-state model, which allow for the
estimation noise of the larger model; a significant test with a negative $R^2$ gain
means the extra predictors carry signal that estimation error currently swamps.*

The 2-year gains come almost entirely from hedge-regime days (+0.94pp at one day), that
is, from the reversal of premium-driven front-end moves. Beyond one day the two-variable
structural state beats the six-variable unrestricted alternative, which is the sense in
which the identification adds parsimony.

**Pre-registered criterion (ii)** asks for a real-time 10-year gain at two or more
horizons. **It fails.** For 2020-2025 alone the regime-specific split does improve the
five-day 10-year forecast (p = 0.02), but that is one horizon in one sub-period.

**Exploratory, not pre-registered:** the curve-state variables damage real-time
forecasts, so the comparison was repeated without them. The regime-specific split still
improves the 2-year at every horizon (Clark-West p ≤ 0.03), but no model beats a
no-change forecast of the 2-year (the split model's out-of-sample $R^2$ lies between
-0.5% and -1.3%). The only material positive out-of-sample $R^2$ against no change is
unrestricted cross-asset news for the slope at five days (+0.3%).

## 4. Decision rule and what follows

| Phase 2 criterion (10-year) | Evidence | Verdict |
|---|---|---|
| (i) Split beats placebo in a majority of draws, one regime, two or more horizons | Best: 44% at one horizon (co-movement, one day) | Fails |
| (ii) Real-time gain at two or more horizons, 2000-2025 | p = 0.41-0.90 | Fails |

By the pre-registered rule, the linear daily design fails for the 10-year in both its
constant and its regime-dependent form. What survives is economically coherent but
small:

- the origin of a move predicts its continuation in the direction theory implies, most
  clearly when bonds and stocks fall together;
- the regime-specific identification is a better description of daily markets and a
  parsimonious real-time state for the 2-year, but not a source of usable forecasts.

The remaining pre-specified route is nonlinearity in the size of news: continuation may
be concentrated on the few days with large policy news (FOMC, CPI, payrolls), which a
daily linear projection averages with thousands of quiet days. It needs its own
pre-registration and an event calendar. If it also fails, the honest paper is a
well-identified null: structural attribution of sovereign yield moves is descriptively
informative but not a state variable for their subsequent dynamics at daily-to-monthly
horizons.

*Implementation.* Regime-specific innovation covariances with inverse-Wishart posteriors
around the common VAR; 1,000 accepted draws per regime in sample, 200 per regime per year
in real time; robustness with a 125-day regime window gives the same picture. Seed
20261006; run time about 90 seconds.
