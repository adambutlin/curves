# Pre-registration: identification and tests for the minimum viable project

*Committed on 4 October 2026, before any structural VAR is estimated on these data.
Nothing below may be changed after estimation without an entry in the deviations log
(Section 9) giving the date, the change and the reason. The commit containing this
file is the reference point for every later claim that a result was not tuned.*

The economic motivation and the critique that shapes these tests are in
[01-research-design.md](01-research-design.md).

---

## 1. Market, data and sample

| Item | Choice |
|---|---|
| Market | US Treasuries (deepest market, longest clean daily data) |
| Yields | Gürkaynak-Sack-Wright zero-coupon yields, continuously compounded, 2, 5 and 10 years (Federal Reserve Board, `feds200628.csv`), changes in basis points |
| Equity | US value-weighted market total return, Kenneth French daily factors (`Mkt-RF + RF`), as a log return in percent |
| Calendar | Trading days on which all four series are observed. Changes and returns are computed between consecutive common days, so a day on which only one market is open folds into the next common day |
| Estimation sample | 3 January 1983 to 31 December 2025. 1983 follows Cieslak and Pang (2021): the Federal Reserve's return to interest-rate targeting |
| Holdout | Every observation dated 1 January 2026 or later is sealed (Section 8) |

Yields and equity enter in different units; no restriction compares a yield response
with an equity response, so the units do not affect identification.

## 2. Reduced form

$$Y_t = c + \sum_{l=1}^{p} A_l Y_{t-l} + u_t,\qquad u_t \sim N(0,\Sigma),\qquad Y_t = (\Delta y^{(2)}_t,\ \Delta y^{(5)}_t,\ \Delta y^{(10)}_t,\ r^{eq}_t)'$$

- **Lags:** baseline $p = 1$ (Cieslak and Pang select one lag by BIC); robustness $p = 5$
  (one trading week; Brandt et al. use four).
- **Prior:** conjugate normal-inverse-Wishart with Minnesota moments, implemented with
  dummy observations (Bańbura, Giannone and Reichlin, 2010). Prior mean zero on every
  lag coefficient, because all variables are already changes or returns. Overall
  tightness $\lambda = 0.2$, lag decay $l^{-1}$, scale $\sigma_i$ from univariate AR($p$)
  residual standard deviations, a diffuse prior on the constant. Robustness:
  $\lambda \in \{0.05, 1\}$.
- **Posterior:** exact draws of $(A, \Sigma)$ from the normal-inverse-Wishart posterior.

## 3. Structural identification

$u_t = B\varepsilon_t$, $E[\varepsilon_t\varepsilon_t'] = I$, $BB' = \Sigma$. Four shocks, after
Cieslak and Pang (2021, Section 2.2):

| Impact of a positive shock on | Growth news (g) | Monetary tightening (m) | Common premium (cp) | Hedging premium (hp) |
|---|---|---|---|---|
| 2-year yield | + | + | + | − |
| 5-year yield | + | + | + | − |
| 10-year yield | + | + | + | − |
| Equity return | + | − | − | − |
| Across maturities | $b_{10} < b_2$ and $b_{10} < b_5$ | $b_2 > b_5 > b_{10}$ | $b_2 < b_5 < b_{10}$ | $\lvert b_2\rvert < \lvert b_5\rvert < \lvert b_{10}\rvert$ |

where $b_n$ is the impact response of the $n$-year yield. The economics: shocks to
short-rate expectations (growth and monetary news) fade with maturity because the
short rate is mean-reverting; risk-premium shocks accumulate with maturity because a
long bond is exposed to every future short-rate shock. Growth news raises both stocks
and yields; monetary tightening raises yields and lowers stocks; a higher common
premium lowers both bond and stock prices; a higher hedging premium lowers stock
prices while bonds rally as a hedge (flight to quality).

*Our operationalisation.* Cieslak and Pang state these restrictions verbally; their
summary table is in an appendix not available to us. We require strict inequalities,
the same sign at all three maturities for every shock, and, for the two premium shocks,
an absolute response that rises strictly with maturity. This reading is at least as
strict as theirs.

**Sampler.** Arias, Rubio-Ramírez and Waggoner (2018), Algorithm 1, sign restrictions
only (no importance weights needed). Joint accept-reject over (reduced form, rotation):
draw $(A, \Sigma)$ from the posterior, draw $Q$ uniformly (Haar) on the orthogonal group
via the QR decomposition of a standard normal matrix, form $B = \operatorname{chol}(\Sigma)Q$,
and keep the draw if its columns can be matched to the four shocks with sign flips.
The four restriction sets are mutually exclusive up to sign, so each column satisfies
at most one shock's restrictions; the matching is therefore unique and the accepted
draws are uniform over the identified set. Target: 1,000 accepted draws. Seed
20261004.

**Reporting.** Every statistic is reported as a distribution over accepted draws (the
identified set combined with reduced-form uncertainty). The Fry-Pagan median-target
draw is used only for single-model figures.

## 4. Decomposition outputs and the learned-from-data check

1. **Variance shares** $B_{ik}^2/\Sigma_{ii}$: the share of each variable's daily
   innovation variance due to each shock.
2. **Replication targets** (Cieslak and Pang, 1983-2017): growth and monetary news
   explain about 80% of 2-year yield variance; risk-premium news about 60% of equity
   variance, growth about 25%, monetary under 20%; a one-standard-deviation monetary
   shock raises the 2-year yield by about 3.6bp on impact. Checked on 1983-2017 and on
   the full sample. Differences in the equity index (CRSP value-weighted versus S&P 500)
   and data vintage mean these are targets, not pass/fail conditions.
3. **Restriction-only benchmark.** Repeat the identification with $\Sigma$ replaced by
   the diagonal matrix of sample variances, which removes all cross-asset covariance
   information. The decomposition is *learned* if the posterior variance shares lie
   materially outside the benchmark distribution; if they coincide, the restrictions
   produce the decomposition and the labels carry no information from the data.

## 5. Propagation tests (in sample, 1983-2025)

**Outcomes.** $r^{(x)}_{t,t+h} = x_{t+h} - x_t$ for $x \in \{y^{(10)},\ y^{(2)},\ y^{(10)} - y^{(2)}\}$
and $h \in \{1, 5, 10, 20\}$ trading days. The day-$t$ move is excluded: these are
subsequent dynamics.

**Controls** $Z_t$, all known at the close of day $t$: the 10-year level, the 2s10s
slope, the change in the 10-year yield over the preceding 20 trading days (excluding
day $t$), and the standard deviation of daily 10-year changes over the same 20 days.

**Inference.** OLS with Newey-West standard errors, $h$ lags.

- **Test A: does the origin matter at all (identification-free)?**
  $r_{t,t+h} = \alpha + \beta\,\Delta x_t + \delta' Z_t + \phi'\tilde u_t + e$, where
  $\Delta x_t$ is the day-$t$ change in the outcome series itself and $\tilde u_t$ are three
  reduced-form innovations completing the span of $u_t$. $H_0: \phi = 0$, Wald test. This
  is the proposal's $H_0$, and its answer is the same under every identification.
- **Test B: shock-specific propagation ratios.**
  $r_{t,t+h} = \alpha + \sum_k \gamma_{k}\,\varepsilon_{k,t} + \delta' Z_t + e$, run for every
  accepted draw. For the 10-year and 2-year yields, $\pi_k = \gamma_k / b_{k}$ is the fraction
  of the day-$t$ move caused by shock $k$ that continues ($\pi_k > 0$) or reverses
  ($\pi_k < 0$) over $h$ days. Reported: the distribution of each $\pi_k$ and the share of
  draws preserving the modal ranking.
- **Test C: a parsimonious structural state.** Split the outcome's day-$t$ innovation
  into expectations-shock and premium-shock contributions,
  $C^{EH}_t = b_g\varepsilon_{g,t} + b_m\varepsilon_{m,t}$ and $C^{TP}_t = b_{cp}\varepsilon_{cp,t} + b_{hp}\varepsilon_{hp,t}$,
  and estimate $r_{t,t+h} = \alpha + \theta_{EH}C^{EH}_t + \theta_{TP}C^{TP}_t + \delta' Z_t + e$.
  $H_0: \theta_{EH} = \theta_{TP}$. **Placebo:** 1,000 uniformly random rotations with no
  restrictions and a random two-plus-two grouping of shocks. The split has structural
  content only if its incremental $R^2$ over the own-move model exceeds the 90th
  percentile of the placebo distribution in a majority of accepted draws.

## 6. Pseudo out-of-sample design

Expanding window. At each year-end $T \in \{1999, \dots, 2024\}$, everything is
re-estimated on data from 3 January 1983 to $T$: VAR posterior, identified set (200
accepted draws, for computing time) and the predictive regressions. Training pairs
satisfy $t + h \le T$, so no training outcome is realised after $T$. Shocks for the
forecast year $T+1$ use the VAR coefficients and impact matrices estimated through $T$
only. Structural forecasts are averaged across accepted draws, which integrates over
the identified set.

| Model | Predictors |
|---|---|
| M0 | none: the martingale forecast of zero change |
| M1 | constant and the own day-$t$ move (momentum or reversal) |
| M2 | M1 plus the curve-state controls $Z_t$ |
| M3 | M2 plus the structural split (premium-shock contribution, equivalently separate $\theta_{EH}, \theta_{TP}$) |
| M4 | M2 plus the full reduced-form innovation vector: the identification-free upper bound for any linear structural state |

**Metrics.** Out-of-sample $R^2$ relative to M0 and relative to M2; Clark-West (2007)
test for nested models (M3 and M4 against M2), Newey-West with $h$ lags; mean absolute
error. Reported for 2000-2025 and the subperiods 2000-2007, 2008-2019 and 2020-2025.

## 7. Decision rules

- **$H_0$ rejected** if Test A rejects at 5% at two or more of the four horizons for the
  10-year yield **and** M4 beats M2 out of sample (Clark-West, 5%) at those horizons.
- **Identification carries information** if (i) the decomposition passes the
  restriction-only benchmark (Section 4.3) and (ii) Test C beats its placebo and M3
  beats M2 out of sample.
- **Otherwise the null is reported.** A failure of Test A at all horizons ends the
  linear version of the project; nonlinear propagation would then be the only remaining
  route, and it would need its own pre-registration.

## 8. Holdout protocol

1. Observations dated on or after 1 January 2026 are sealed. The estimation data layer
   refuses to return them unless called with an explicit unseal flag.
2. The holdout is opened only after (i) the in-sample and pseudo out-of-sample results
   are committed, (ii) the end-2025 model is frozen (accepted draws saved to disk with
   their hash recorded in the results note), and (iii) the project owner approves.
3. **Contamination disclosure.** 2026 data have already been seen in the earlier
   descriptive work (see [01-research-design.md](01-research-design.md), Section 2.5):
   between 27 February and 19 August 2026 the US 10-year rose 68bp, of which the NY Fed's
   published ACM model attributes 51bp to expected rates and 17bp to term premium. The
   restrictions above are Cieslak and Pang's published scheme, adopted without
   modification beyond the operationalisation stated in Section 3, which limits the scope
   for unconscious tuning toward that knowledge.

## 9. Deviations log

| Date | Change | Reason |
|---|---|---|
| 4 Oct 2026 | Section 4.3 benchmark: instead of a fully diagonal $\Sigma$, keep the yield-curve block and set only the yield-equity covariances to zero | With a diagonal $\Sigma$ the restrictions cannot be satisfied at all: every shock moves the three yields in the same direction, which requires positive covariance across maturities (rows of an orthogonal matrix with matching signs cannot be orthogonal). Found on first estimation. The amended benchmark removes exactly the cross-asset information the check was meant to isolate |
| 4 Oct 2026 | Test B also reports the drift $\gamma_k$ in basis points, not only the ratio $\pi_k = \gamma_k/b_k$ | The ratio is unstable where a shock barely moves the outcome on impact. Reporting only; no test changed |
| 4 Oct 2026 | Exploratory analyses added after estimation: closing-time lead-lag, outcomes that skip the first day, the benchmark within each stock-bond regime, Test A on constant-maturity yields | To separate economic results from measurement effects. Labelled exploratory in the results note; no pre-registered result was replaced |

## 10. Pre-specified extensions (not part of the MVP)

- Inflation compensation (10-year breakeven, daily from 2003) to separate inflation
  news from real-rate news.
- A Brandt-style US block with the broad dollar (daily from 2006): risk-off shocks
  appreciate the dollar, which separates them from bad growth news.
- The expectations-versus-term-premium mechanism using the NY Fed's daily ACM
  decomposition and the project's own ACM model.
- UK gilts and German Bunds, with domestic versus foreign origin identified by
  magnitude restrictions on cross-country spreads (Brandt et al., Table 1).
