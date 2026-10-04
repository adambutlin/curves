# Phase 2 pre-registration: regime-dependent identification and propagation

*Written on 4 October 2026, after the MVP results and before any regime-dependent
estimation. Provisional: the project owner has not yet chosen between redesign and
abandonment, and this phase is the evidence for that choice. Deviations go in
Section 7.*

## 1. Why this design, and what it cannot claim

The MVP ([03-mvp-results.md](03-mvp-results.md)) found three things that motivate it:

1. The covariance that separates the shocks changes sign around 2000: the daily
   correlation of 10-year yield changes with equity returns is -0.31 in 1983-1999 and
   +0.29 in 2000-2025. One impact matrix for the whole sample pools a regime in which
   bonds and stocks rose and fell together with one in which Treasuries hedged equity
   risk. Within each regime that misallocates shocks, mostly between the two premium
   shocks. This is a modelling approximation with economic consequences, and fixing it
   is worthwhile whatever the propagation result.
2. The only real-time forecasting gains came in 2020-2025, which includes the return of
   a regime in which inflation risk made bonds and stocks fall together.
3. The economics of the two regimes differ (Campbell, Pflueger and Viceira, 2020): when
   supply and inflation shocks dominate, nominal bonds are risky; when demand shocks
   dominate, they hedge. There is no reason to expect the same propagation in both.

**Disclosure.** These hypotheses were formed after seeing the 1983-2025 results, so
in-sample evidence on the same data is weaker than the MVP's. The real-time evaluation
below is fully specified here and cannot be tuned afterwards, but its forecast period
(2000-2025) has also been seen. The only unseen data remain 2026, which stays sealed.

## 2. The regime, measured in real time

$$\rho_t = \operatorname{corr}\big(\Delta y^{(10)}_s,\ r^{eq}_s\big),\qquad s = t-250, \dots, t-1,$$

the correlation over the previous 250 trading days, excluding day $t$.
**Hedge regime** ($\mathcal H$): $\rho_t > 0$, yields fall when stocks fall, so
Treasuries hedge equity risk. **Co-movement regime** ($\mathcal C$): $\rho_t \le 0$,
bonds and stocks fall together. Robustness: a 125-day window.

## 3. Identification

The same VAR(1), prior and sign restrictions as the MVP (pre-registration Sections 2
and 3), with one change: the innovation covariance is regime-specific. With $u_t$ the
VAR innovations at the posterior-mean coefficients and $T_R$ the number of days in
regime $R$,

$$\Sigma_R \sim \mathcal{IW}\Big(\textstyle\sum_{t \in R} u_t u_t',\ T_R\Big),\qquad u_t = B_{R_t}\varepsilon_t,\qquad B_R B_R' = \Sigma_R,$$

and the impact matrix of each regime is set-identified by the same sign restrictions,
1,000 accepted draws per regime, paired by draw index. Day-$t$ shocks use the impact
matrix of the regime prevailing on day $t$.

## 4. Tests

All outcomes, horizons, controls and inference as in the MVP (Section 5 there).

- **A-R.** The identification-free test, run separately on days of each regime.
- **C-R.** The expectations/premium split built from the regime-specific impact matrices,
  run separately on days of each regime, with its own placebo (1,000 random rotations of
  that regime's covariance with random two-plus-two groupings).
- **Comparison with the MVP.** Whether the share of draws beating the placebo rises when
  the identification respects the regime.

## 5. Real time

As in the MVP (expanding window, re-estimated at each year-end 1999-2024, forecasts for
2000-2025, 200 accepted draws per regime per year), with the regime indicator computed in
real time and both impact matrices estimated only on training days of each regime.

| Model | Predictors |
|---|---|
| M2 | own move and curve state (as in the MVP) |
| M3R | M2 plus the premium-shock contribution from the regime-specific identification, with a separate coefficient in each regime |
| M4R | M2 plus the other three reduced-form innovations, each interacted with the regime: the identification-free upper bound |

Metrics as in the MVP: out-of-sample $R^2$ against no change and against M2;
Clark-West tests of M3R and M4R against M2.

## 6. Decision rule

Regime dependence **supports the redesign** if, for the 10-year yield, (i) Test C-R
beats its placebo in a majority of accepted draws in at least one regime at two or more
horizons, **and** (ii) M3R improves on M2 out of sample (Clark-West, 5%) at two or more
horizons over 2000-2025. If only (i) holds, the regime-specific decomposition is better
but still not useful in real time. If neither holds, the linear daily design fails in
both its constant and its regime-dependent form, and the remaining route is
nonlinearity in the size of news, which would need its own pre-registration.

## 7. Deviations log

| Date | Change | Reason |
|---|---|---|
| (none yet) | | |
