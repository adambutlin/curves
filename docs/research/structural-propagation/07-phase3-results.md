# Phase 3 results: propagation and the size of the news

*US Treasuries and equities, daily, 1983-2025; 2026 sealed. Estimated on 4 October 2026
under [06-phase3-size-preregistration.md](06-phase3-size-preregistration.md), hashed
before estimation (01:59 UTC, SHA-256 `bc536fc2...3a759`). Tables:
`reports/structural_propagation/phase3/`.*

---

## Conclusion

1. **The hypothesis fails in the predicted direction and holds in the opposite one.**
   Large news about policy-rate expectations does not continue more than ordinary news.
   At the 2-year and in the 2s10s slope it continues *less*: whatever continuation
   exists sits in ordinary-sized news, while large, salient moves are priced at once
   and, in the slope, partly reversed.
2. **By the pre-registered rule the size route is closed**, and with it the
   daily-propagation question for the 10-year: across a constant identification, a
   regime-specific one and a size-dependent one, structural origin is not a usable
   state variable for 10-year dynamics at 1-20 day horizons.
3. **The surviving economic content is a salience pattern**, not a forecasting rule:
   small policy news diffuses gradually, large policy news does not. This is consistent
   with limited-attention models of underreaction, and it was not hypothesised in
   advance, so it is an interpretation to test, not a finding to claim.

---

## 1. Design

Each day's innovation in the outcome is split into the parts due to short-rate-
expectations shocks ($C^{EH}_t$) and to premium shocks ($C^{TP}_t$), as in the MVP. A day
is *large* for a component when that component exceeds two of its standard deviations
(about 5% of days):

$$r_{t,t+h} = \alpha + \beta\,\Delta x_t + \kappa\,C^{TP}_t + \lambda_{EH}\,C^{EH}_t L^{EH}_t + \lambda_{TP}\,C^{TP}_t L^{TP}_t + \delta' Z_t + e_{t+h},$$

where $L^{EH}_t$ and $L^{TP}_t$ indicate large days. $\lambda_{EH}$ is the *extra*
continuation of large expectations news over ordinary expectations news. The hypothesis
predicted $\lambda_{EH} > 0$.

## 2. Results

| $\lambda_{EH}$ (median, 90% of identified set) | h = 1 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| 10-year | -0.06 [-0.17, 0.08] | -0.08 [-0.19, 0.40] | 0.02 [-0.16, 0.46] | 0.09 [-0.12, 0.87] |
| 2-year | -0.07 [-0.10, -0.02] | -0.15 [-0.22, -0.01] | -0.13 [-0.24, 0.02] | -0.12 [-0.28, 0.12] |
| 2s10s slope | -0.05 [-0.10, -0.02] | -0.21 [-0.36, -0.06] | -0.24 [-0.50, -0.08] | -0.38 [-0.65, -0.11] |

- **10-year:** no extra continuation of large policy news; $t > 1.96$ in at most 4% of
  admissible draws. Criterion (i) fails.
- **2-year:** large expectations news continues *less* than ordinary news over one to
  five days, robustly across the identified set. Against an average continuation of
  roughly 0.08 at those horizons in the MVP, a large policy move at the front end is
  followed by no further drift, or a small reversal, within a week.
- **Slope:** the shortfall grows with the horizon, from 0.05 at one day to 0.38 over a
  month, with every 90% band excluding zero. Against an average continuation of about
  0.37 over a month in the MVP, large expectations-driven steepenings or flattenings
  essentially do not continue at all.
- **Large premium shocks** show no robust extra reversal, the hypothesised sign, at any
  horizon (fewer than 6% of draws).

**Against the placebo** (random rotations with random groupings and the same size
thresholds), the size terms beat the 90th percentile in at most 36% of draws for the
10-year; criterion (ii) fails. The one majority in the whole exercise is a robustness
case (the slope at 20 days with a 1.5 standard-deviation threshold, 53%), which is not
the pre-registered specification.

**Real time, 2000-2025:** adding the size terms improves the 10-year forecast at one
horizon only (ten days, Clark-West p = 0.01, +0.10pp of $R^2$); criterion (iii) fails.
In 2020-2025 the gains are larger at one and five days (p = 0.05 and 0.003), the same
sub-period that stood out in the MVP and in Phase 2.

## 3. Interpretation and caveats

The result reverses the motivating intuition. A model of limited attention predicts it
naturally: investors react fully to salient news (a large FOMC surprise, a large payroll
miss) and only gradually to the steady flow of small items (speeches, minor data), so
underreaction is concentrated where news is small. The post-FOMC drift in the literature
is measured from the announcement day; here, the large-news days absorb their news on
the day.

Two caveats, in order of importance:

1. **Large relative to the full sample is partly "early in the sample".** The threshold is
   a full-sample (or training-sample) standard deviation, so large days cluster in the
   high-volatility 1980s and in crises. Part of the shortfall could reflect a different
   era rather than the size of news. *Exploratory check:* with large days defined relative
   to the previous 250 days' volatility, the shortfall survives at about half the size in
   the slope (-0.16 at five days and -0.13 at ten, bands excluding zero) and in full at the
   2-year over one day (-0.06, band [-0.09, -0.03]); the hypothesised extra continuation
   is absent everywhere ($t > 1.96$ in at most 2% of draws). Roughly half of the slope
   effect is the era, half the size of the news.
2. **This pattern was not pre-registered as a hypothesis.** It is the sign the data
   chose after three rounds of testing on the same sample. It should be treated as a
   hypothesis for an independent test (another market, or 2026), not as a result.

## 4. Where the three phases leave the project

| Question | Answer |
|---|---|
| Can the structural decomposition be replicated and trusted? | Yes: Cieslak and Pang reproduced almost exactly; the regime-specific version is economically sharper |
| Does origin predict the direction of subsequent moves? | Yes, in sign: policy-expectations news continues, premium news does not, especially when bonds and stocks fall together |
| Is that predictability economically usable for the 10-year? | No, in any of the three pre-registered designs |
| Anything usable anywhere? | The regime-specific split improves real-time 2-year forecasts relative to a curve-state model, but no model beats a no-change forecast |

The daily-propagation hypothesis, as a forecasting claim about the 10-year, is answered
in the negative. The decomposition itself remains a credible, replicated tool for
attributing moves, which is what the 2026 application needs.
