# Phase 3 pre-registration: does propagation depend on the size of the news?

*Written on 4 October 2026 after the MVP and Phase 2 results, before any size-dependent
estimation. Provisional, like Phase 2. Deviations go in Section 6.*

## 1. Hypothesis and disclosure

Continuation of policy news is documented around large, scheduled announcements (the
post-FOMC drift of Brooks, Katz and Lustig) rather than on ordinary days. A daily linear
projection averages the few days of large news with thousands of quiet days, which may be
why the MVP found the right sign but a negligible magnitude.

> **H3:** the part of a day's yield move caused by *large* news about short-rate
> expectations continues by more than the same part on ordinary days; large premium
> shocks reverse.

This was formed after the MVP and Phase 2, on the same data, and is the last
pre-specified route in [03-mvp-results.md](03-mvp-results.md) (Section 7). No event
calendar is used: "large" is defined by the size of the identified news itself, which
makes the test depend on the identification (a rotation changes which days are large).
The 2026 holdout stays sealed.

## 2. Large-news days

With the MVP identification (constant impact matrix, pre-registration Sections 2-3) and
$C^{EH}_t$, $C^{TP}_t$ the expectations-shock and premium-shock parts of the day-$t$
innovation of the outcome series,

$$L^{EH}_t = \mathbf 1\{|C^{EH}_t| > 2\,\sigma_{EH}\},\qquad L^{TP}_t = \mathbf 1\{|C^{TP}_t| > 2\,\sigma_{TP}\},$$

where $\sigma_{EH}$ and $\sigma_{TP}$ are the standard deviations of the two parts over
the estimation (or, in real time, training) sample. Robustness thresholds: 1.5 and 2.5.

## 3. Test

$$r_{t,t+h} = \alpha + \beta\,\Delta x_t + \kappa\,C^{TP}_t + \lambda_{EH}\,C^{EH}_t L^{EH}_t + \lambda_{TP}\,C^{TP}_t L^{TP}_t + \delta' Z_t + e_{t+h},$$

all other choices as in the MVP (outcomes, horizons, controls, Newey-West with $h$ lags,
1,000 accepted draws). H3 predicts $\lambda_{EH} > 0$ and $\lambda_{TP} < 0$.

**Placebo:** 1,000 uniformly random rotations with random two-plus-two groupings, the
same size thresholds applied to the random groups. Statistic: the incremental $R^2$ of
the two size terms over the MVP split model.

**Real time:** as in the MVP (expanding window, 2000-2025, 200 draws per year, thresholds
from training data only). Model M5 = M3 plus the two size terms; compared with M2 and M3
by Clark-West tests.

## 4. Decision rule

H3 is **supported** for the 10-year yield if (i) $\lambda_{EH} > 0$ with $t > 1.96$ in a
majority of accepted draws at two or more horizons, (ii) the size terms beat the 90th
percentile of the placebo in a majority of draws at two or more horizons, and (iii) M5
improves on M2 in real time (Clark-West, 5%) at two or more horizons. If (i) holds
without (ii) or (iii), the size effect is real but not specific to the identification or
not usable. If (i) fails, the size route is closed and the daily-propagation question
is answered in the negative.

## 5. Interpretation guard

Large premium-shock days include episodes of market dysfunction (October 1987, March
2020) in which fitted yields are noisy; a reversal of large premium moves is reported
separately from any economic interpretation, with the constant-maturity yields as a check
if it drives the result.

## 6. Deviations log

| Date | Change | Reason |
|---|---|---|
| (none yet) | | |
