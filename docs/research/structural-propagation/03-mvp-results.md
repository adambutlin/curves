# MVP results: does the origin of a Treasury yield move predict what follows?

*US Treasuries and the US equity market, daily, 3 January 1983 to 31 December 2025
(10,720 trading days). 2026 remains sealed. Estimated on 4 October 2026 under the
pre-registration in [02-identification-preregistration.md](02-identification-preregistration.md).
Figures and tables: `reports/structural_propagation/`.*

---

## Conclusion

1. **The origin of a daily Treasury move does carry information about what follows,
   and its direction is economically coherent.** The part of a day's yield move caused
   by news about the expected course of policy rates (growth and monetary news)
   continues over the following days and weeks; the part caused by risk-premium shocks
   does not. This holds in sign in 89-99% of admissible identifications, depending on
   the horizon.
2. **The information is economically negligible and does not survive in real time
   for the 10-year yield.** Cross-asset news explains at most 0.4% of the variance of
   subsequent 1-20 day changes, and no forecasting model beats a no-change forecast of
   the 10-year or 2-year yield over 2000-2025. Under the pre-registered decision rule
   **the null is not rejected for the primary outcome**.
3. **The economically labelled decomposition is not special.** Random splits of the
   same daily cross-asset news predict as well as the expectations/premium split. The
   linear, constant-coefficient, daily version of the hypothesis therefore fails the
   minimum viable test. The evidence points instead to state dependence: the only
   period in which cross-asset structure helped in real time is 2020-2025, the years
   of the inflation shock, when bond and stock returns were again positively correlated.

**Recommendation:** redesign rather than abandon. The next design should be
pre-registered around state-dependent propagation with regime-specific identification
(Section 7), before any international extension, with 2026 still sealed.

---

## 1. The decomposition: replicated, with yield shares driven by the maturity restrictions

The four shocks are those of Cieslak and Pang (2021): growth news, monetary news,
a common risk premium (bonds and stocks fall together) and a hedging premium (stocks
fall, Treasuries rally as a hedge). They are identified from daily changes in the 2-,
5- and 10-year zero-coupon yields and the equity return by sign restrictions and by
how each shock's impact varies across maturities: shocks to short-rate expectations
fade with maturity, risk-premium shocks build with it.

**Result: the published decomposition is reproduced almost exactly on its own sample.**

| 1983-2017 | Cieslak and Pang | This model |
|---|---|---|
| Share of 2-year variance from growth plus monetary news | about 80% | 77% |
| Share of equity variance from the two premium shocks | nearly 60% | 58% |
| Share of equity variance from growth news | about 25% | 22% |
| Share of equity variance from monetary news | under 20% | 10% |
| 2-year impact of a one-standard-deviation monetary shock | 3.6bp | 3.55bp |

The replication succeeds, so the identification layer is a faithful implementation of
the published scheme. On 1983-2025 the shares barely change: growth and monetary news
explain 69% of 2-year variance and the two premium shocks 75% of 10-year variance
(Figure 1).

**Caveat 1: the identified set is wide.** Across admissible rotations the share of
2-year variance due to growth news runs from 4% to 71%. Any statement about a single
shock that is not robust across this range is a statement about the prior over
rotations, not about the data.

**Caveat 2: what the data teach.** Removing all stock-bond co-movement from the
estimated covariance (keeping the yield-curve block) leaves the full-sample shares
almost unchanged: hedging premium 39% versus 36% of 10-year variance, growth news 21%
versus 16% of equity variance. The reason is economic, not numerical: the stock-bond
correlation changed sign around 2000 (daily correlation of 10-year yield changes with
equity returns of -0.31 in 1983-1999 and +0.29 in 2000-2025), so over the whole sample
the two regimes cancel. Within each regime the cross-asset information matters a great
deal: in 2000-2025 the hedging premium explains 37% of equity variance with the
estimated covariance and 19% without it; in 1983-1999 the common premium explains 52%
with it and 26% without. The yield shares, by contrast, are pinned down by the maturity
restrictions in either regime.

This exposes a **modelling approximation** with economic consequences: a single impact
matrix for 1983-2025 pools a regime in which bonds and stocks rose together with one in
which Treasuries were the hedge. Shocks are then misallocated within each regime,
mainly between the two premium shocks. Any propagation result that depends on the
common/hedging distinction is weakened by this, which matters for the redesign.

## 2. Does origin matter at all? (identification-free test)

In a linear system the null that origin is irrelevant has the same answer under every
identification, because any rotation of the daily innovations spans the same space:

$$r_{t,t+h} = \alpha + \beta\,\Delta x_t + \delta' Z_t + \phi'\tilde u_t + e_{t+h},\qquad H_0:\ \phi = 0,$$

where $r_{t,t+h}$ is the change in yield or slope from the close of day $t$ to day
$t+h$ (the day-$t$ move excluded), $\Delta x_t$ the observed day-$t$ change of the same
series, $Z_t$ the curve state (10-year level, 2s10s slope, prior 20-day change and
volatility), and $\tilde u_t$ the other three daily innovations of the VAR.

**Result: the null is rejected, but the magnitudes are tiny.**

| Outcome | h = 1 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| 10-year: p-value | 0.005 | 0.0001 | 0.02 | 0.34 |
| 10-year: incremental $R^2$ | 0.23% | 0.20% | 0.10% | 0.03% |
| 2s10s slope: p-value | 0.36 | <0.0001 | <0.0001 | <0.0001 |
| 2s10s slope: incremental $R^2$ | 0.07% | 0.38% | 0.40% | 0.41% |
| 2-year: p-value | 0.06 | 0.19 | 0.45 | 0.06 |

Cross-asset news predicts the 10-year over one to ten days and the slope over one to
four weeks; the 2-year shows nothing at conventional levels. In economic units the
10-year effect is small: an incremental $R^2$ of 0.2% at five days moves the expected
five-day change by about 0.6bp per standard deviation of the predictor, against a
realised five-day standard deviation of about 14bp.

Two checks show these rejections are not artefacts of market closing times or of how the
curve is constructed.

- **Closing times.** Treasury closing marks are typically taken before the 4pm equity
  close, which could
  make today's late equity news show up in tomorrow's yields. The sign is wrong for that
  story (tomorrow's 10-year change falls by 0.19bp per 1% equity rise, t = -1.4), and
  dropping the first day leaves the five-day 10-year rejection intact (p = 0.004) and
  the slope rejections unchanged.
- **Curve construction.** On the Treasury's constant-maturity par yields (fitted to
  on-the-run securities) instead of the Gürkaynak-Sack-Wright zero curve (fitted to
  off-the-run securities), the 10-year rejections survive at one and five days (p = 0.03
  and 0.01) and the slope rejections at five to twenty days (p ≤ 0.001). One number does
  move: the reversal of a day's own 10-year move, holding the 2- and 5-year fixed, halves
  from -0.28 to -0.14 of the move over five days. **About half of that reversal depends
  on how the curve is built**, so it is a measurement issue until confirmed on traded
  securities; what remains is consistent with temporary long-end price pressure, for
  example around auctions.

## 3. How does each origin propagate?

For each admissible identification, the subsequent change is projected on the four
shocks; $\gamma_k$ is the drift in basis points per one-standard-deviation shock and
$\pi_k = \gamma_k/b_k$ the drift as a fraction of the shock's impact $b_k$ (Figure 2).

**Result: news about policy-rate expectations continues; only signs are robust.**

- **2-year, 20 days:** a one-standard-deviation growth shock (impact +3.0bp) is followed
  by a further +1.0bp, and a monetary shock (impact +3.5bp) by a further +0.9bp: roughly
  a third and a quarter of the initial move. Positive in 99% and 97% of admissible draws.
  A flight to quality (hedging premium; impact -2.0bp) is followed by a further -0.9bp
  (negative in 95% of draws), consistent with risk-off episodes being followed by
  expected policy easing.
- **10-year:** monetary news continues the next day (+0.30bp on an impact of 1.5bp,
  positive in every draw); growth news keeps moving the 10-year for a month (+0.58bp
  over 20 days on an impact of 1.6bp, positive in 99% of draws).
- **Premium shocks** show no consistent continuation. At the 10-year a flight to quality
  partially reverses within a week (about 8% of its impact, in 99.9% of draws) before
  drifting the other way over the month; a common-premium shock adds about 5% of its
  impact the next day. At the 2-year the common premium reverses about a fifth of its
  impact within a week (95% of draws).

This is the pattern a model of gradual information diffusion predicts for news about
the policy-rate outlook (the post-FOMC drift of Brooks, Katz and Lustig is one
instance), and the absence of continuation is what a model of transient risk-bearing
capacity predicts for premium shocks.

**Caveat: the full ordering of the four shocks is not identified.** The modal ranking
of the propagation ratios holds in only 22-43% of admissible draws for the 10-year, so
the pre-registered robustness condition for rankings fails. The ratios themselves are
unstable wherever a shock barely moves the yield on impact (monetary news at the
10-year in some draws): that is a numerical consequence of dividing by a small impact,
which is why the drifts in basis points are the quantities to read.

## 4. A two-dimensional structural state: expectations versus premium

Split the day-$t$ innovation of each series into the part due to shocks to short-rate
expectations and the part due to premium shocks, $u_t = C^{EH}_t + C^{TP}_t$, and let
each propagate at its own rate:

$$r_{t,t+h} = \alpha + \theta_{EH}\,C^{EH}_t + \theta_{TP}\,C^{TP}_t + \delta' Z_t + e_{t+h}.$$

It is estimated as $r_{t,t+h} = \alpha + \beta\,\Delta x_t + \kappa\,C^{TP}_t + \delta' Z_t + e_{t+h}$,
so that $\theta_{EH} = \beta$ and $\theta_{TP} = \beta + \kappa$; the two forms coincide up to
the small part of $\Delta x_t$ that the VAR predicts from the previous day.

**Result: the split points the right way robustly, but it is not special.**

| 10-year | h = 1 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| $\theta_{EH}$ (median) | 0.09 | 0.10 | 0.10 | 0.17 |
| $\theta_{TP}$ (median) | 0.03 | -0.05 | -0.02 | 0.08 |
| Share of draws with $\theta_{TP} < \theta_{EH}$ | 92% | 99% | 95% | 89% |
| Incremental $R^2$ (median) | 0.06% | 0.08% | 0.03% | 0.01% |
| Share of draws beating the 90th percentile of random splits | 3% | 5% | 2% | 4% |

A 10bp rise in the 10-year driven by policy-rate news is followed by roughly another
1bp over the next one to two weeks, and by about 1.7bp over a month; the same rise driven
by premium shocks is followed by roughly a half-basis-point reversal within a week. For
the 2s10s slope the asymmetry is larger: 37% of an expectations-driven slope move
continues over 20 days against 5% of a premium-driven one (asymmetry in 97% of draws).

But random rotations of the same daily news, split arbitrarily into two parts, achieve
the same incremental $R^2$ (Figure 3). The pre-registered criterion, beating the 90th
percentile of random splits in a majority of draws, fails at every horizon and for every
outcome (at most 11% of draws). The economic reading is that daily cross-asset news has
small predictive content spread across several directions; the expectations/premium
direction is one of them, economically coherent, but not the privileged one.

## 5. Real time, 2000-2025

Every model is re-estimated each year-end on data available at the time, including the
identified set, and forecasts the following year (Figure 4).

**Result: no model reliably beats a no-change forecast.**

- For the 10-year, out-of-sample $R^2$ against a no-change forecast is negative for every
  model and horizon (between -0.1% and -1.3%). Adding the structural split to the
  curve-state model changes out-of-sample $R^2$ by less than 0.1 percentage point; adding
  all cross-asset news is not significant either (Clark-West p = 0.06 at one day, 0.30 at
  five).
- The curve-state variables do damage in real time (down to -5% for the 2-year at 20
  days): yield-curve predictors that look stable in sample do not travel.
- **The slope is the exception:** cross-asset news improves on the curve-state model at
  5, 10 and 20 days (Clark-West p = 0.003, 0.007, 0.004), although still not on a
  no-change forecast.
- **2020-2025 is different:** the curve-state model beats a no-change forecast of the
  10-year (out-of-sample $R^2$ of +0.5%, +1.1% and +1.8% at 5, 10 and 20 days), and both
  the structural split and the full cross-asset news improve on it at one and five days
  (Clark-West p between 0.0004 and 0.03). In the years when inflation risk returned and
  bonds and stocks fell together, the structure of daily news did help forecast yields.

## 6. Pre-registered decision rules

| Rule | Evidence | Verdict |
|---|---|---|
| $H_0$ rejected for the 10-year: Test A at 5% at two or more horizons **and** real-time improvement at those horizons | Test A rejects at 1, 5, 10 days; real-time p = 0.06, 0.30, 0.32 | **Not rejected** |
| Same rule for the 2s10s slope (secondary) | Test A rejects at 5, 10, 20 days; real-time p = 0.003, 0.007, 0.004 | Rejected (secondary outcome) |
| Decomposition learned from data | Full sample: barely moves without stock-bond covariance; within regimes: moves materially | Partly |
| Identification carries predictive information: beats placebo and improves forecasts in real time | Beats placebo in at most 11% of draws; improves 10-year forecasts only in 2020-2025 | **No** |

## 7. What this means for the project

The project's premise survives in a weaker form. Origin is associated with propagation
in the direction economics predicts, but in a linear, constant-coefficient daily model
the association is too small to matter and the labelled decomposition adds nothing over
an arbitrary one. Two findings point to where a stronger result could live:

1. **Regime dependence.** The cross-asset information that identifies the shocks changes
   sign around 2000, and the only real-time gains appear in 2020-2025. A model with
   regime-specific impact matrices (identified within each stock-bond regime) and
   regime-dependent propagation is the natural redesign. This also fixes the pooling
   problem in Section 1.
2. **Nonlinearity in the size of news.** Large policy-news days (FOMC, payrolls, CPI) are
   where continuation is documented in the literature; a daily linear projection averages
   them with thousands of noise days. Size and event-day interactions are rotation
   dependent, so they are also a sharper test of the identification.

Both are new hypotheses and need their own pre-registration; the international extension
should wait until one of them works in the US. The 2026 holdout stays sealed.

## 8. Caveats

- Multiple comparisons: 12 outcome-horizon pairs per test. With a Bonferroni threshold
  of 0.004, the five-day 10-year rejection and the 5-20 day slope rejections in Section 2
  survive; the others do not.
- One market and one identification scheme. Inflation news is not separately identified;
  breakevens (from 2003) are the pre-specified extension.
- Maturity-specific moves depend partly on how the curve is constructed (Section 2);
  conclusions about the slope should be confirmed on traded instruments.

## 9. Holdout status and reproducibility

- 2026 observations were never loaded: the data layer refuses dates from 1 January 2026
  unless explicitly unsealed.
- The end-2025 model is frozen: 1,000 admissible draws of the impact matrix, covariance
  and VAR coefficients, SHA-256
  `cafa5f25144f8a4946f69cdf099c54be9709f8824b90f4c2aeb44d317765e7b8`.
- The pre-registration was hashed before any estimation (4 October 2026, 01:22 UTC;
  SHA-256 `4c19a2a1...a8694b`). The commit intended to timestamp it was blocked by the
  environment, so the hash is the audit trail until the files are committed.
- Exploratory analyses (closing times, skipping the first day, regime benchmark,
  constant-maturity yields) were added after estimation and are labelled as such.

*Implementation.* Conjugate Minnesota BVAR by dummy observations; Arias, Rubio-Ramírez
and Waggoner (2018) accept-reject sampling of Haar rotations (acceptance about 2%);
local projections with Newey-West errors; expanding-window real-time evaluation with
Clark-West tests. Seed 20261004. The full run takes about two minutes.
