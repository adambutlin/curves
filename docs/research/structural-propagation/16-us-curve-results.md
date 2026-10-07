# The 2026 Treasury selloff along the curve, through the cross-Atlantic model

*Pre-registration [15-us-curve-preregistration.md](15-us-curve-preregistration.md)
(committed `dad0e57` before estimation). Model A: the synchronised cross-Atlantic model
frozen in `ee532fe` (SHA-256 `4b204619...79d489`); tenor and ACM loadings frozen in
`881e10e` (SHA-256 `3015f33c...467158`) before any 2026 tenor observation was read. Data
to 5 October 2026. Tables: `reports/structural_propagation/us_curve/`; figures 18-22.*

---

## Conclusion

1. **The 2026 Treasury selloff was US news, and mostly US macro news.** Of the 10-year's
   117bp rise in 2026 to date, US news accounts for 96bp (90% of the identified set: 31
   to 119), improving global risk sentiment for 21bp, and euro-area news for nothing. The
   5- and 30-year look the same. The split between US macro and US monetary news is not
   robust across the identified set; the US origin is.
2. **The front end rose by more than any cross-asset shock can explain, and that is the
   flattening.** The 2-year rose 139bp, of which the five shocks explain 74bp; the
   remaining 65bp is front-end-specific news that does not move equities, the dollar or
   the 10-year in a recognisable pattern. Every identified shock steepens the curve, so
   the 22bp flattening of 2s10s is entirely this unspanned front-end repricing.
3. **The structural and the yield-curve decompositions agree once the right comparison is
   made.** The NY Fed's model puts 79% of the 10-year's rise in expected rates; the
   structural model puts 82% in US news. In 2026 the US-news component moves month by
   month with ACM expected rates, not with the term premium. The pre-registered bridge,
   which carries 2007-2025 loadings into 2026, fails for exactly that reason.
4. **The structure explains each day's move and predicts nothing.** The frozen loadings
   explain as much of daily 2026 yield changes as they did in sample (59-92%), but no
   model, structural or not, beats a no-change forecast at any maturity or horizon.

---

## 1. Specification

Model A is Brandt et al.'s five-shock model on prices recorded at the New York close,
with their own euro-area rate (10-year OIS), frozen at end-2025. It is preferred to the
Bund-future variant because its median-target model reproduces the paper's event
attributions (15 of 18 against 4 of 18). The model contains one Treasury yield; the 2-,
5-, 10- and 30-year H.15 yields are attached by projecting each day's change on the five
shocks and their first two lags (the lags absorb the H.15 yields' earlier recording time,
see the pre-registration). The identification is untouched. "Unspanned" is the part of a
move that is not a linear function of the shocks.

**How much of each maturity the structure represents** (daily $R^2$, 2007-2025): 2-year
52%, 5-year 81%, 10-year 91%, 30-year 80%. The model is identified from 10-year rates,
equities and the dollar, so it is a long-rate model; the front end carries policy-path
news of its own.

## 2. Object 1: cumulative decomposition

| 2026 to date (to 5 Oct) | Actual | US news [90%] | of which macro / monetary | Global risk | Euro area | Unspanned |
|---|---|---|---|---|---|---|
| 2-year | +139 | +65 [25, 80] | +50 / +16 | +9 | 0 | +65 |
| 5-year | +138 | +93 [32, 114] | +67 / +26 | +17 | -1 | +28 |
| 10-year | +117 | +96 [31, 119] | +67 / +29 | +21 | -2 | +1 |
| 30-year | +85 | +85 [25, 106] | +59 / +25 | +22 | -2 | -20 |

Over 27 February-19 August the pattern is the same at a smaller scale (10-year +68bp: US
+57, global +13; 2-year +81bp: US +40, unspanned +35).

**Reading.** The long end moved on US news and on improving risk sentiment, which removes
the safe-haven bid (a positive global-risk contribution means risk appetite *rose*).
Euro-area news contributed nothing at any maturity, consistent with document 12's finding
that the euro-area selloff was imported from the US rather than the reverse.

## 3. Object 2: when the driver changed

Rolling 20-day leader, kept for at least 10 trading days (figure 19):

- **US macro news led for most of the year**, at every maturity: February, mid-March, May,
  July and from late August to October.
- **US monetary news led from 22 June to 9 July** at the 5-, 10- and 30-year.
- **Global risk led from 4 to 25 August**: an improvement in risk sentiment that raised
  long yields while the US news flow paused.
- **The September leg was US macro news**: +33bp of the 10-year's +54bp in September.
  At the 2-year it explains +25bp of +54bp; the rest is again unspanned.

The month-by-month leader within US news is the same shock in only 20-60% of admissible
models, so "macro versus monetary" is a description of the median-target model, not a
robust finding. That US news led is robust.

## 4. Object 3: front end against long end

- **Curve signatures (2007-2025).** Every shock loads more on the 10-year than on the
  2-year: a one-standard-deviation US macro shock moves the 2-year 2.9bp and the 10-year
  3.9bp; US monetary 1.6bp and 2.9bp; global risk -1.0bp and -2.4bp. So every identified
  shock steepens 2s10s when it raises yields.
- **2s10s, 2026 to date: -22bp.** The shocks steepened it by 43bp (US +31, global +12);
  unspanned front-end news flattened it by 64bp.
- **10s30s: -32bp.** US news -12bp [-14, -6] (US shocks peak at 5-10 years), unspanned
  -21bp.

**Economic reading.** The selloff was a bear flattening, and the flattening came from the
front end repricing the policy path by more than the day-by-day cross-asset news implied.
News that moves 2-year yields without moving equities or the dollar is what one expects
from a gradual revision of the expected policy path: data releases priced mainly at the
front end, and Fed communication. Brandt et al.'s monetary shock, identified from the
10-year, does not represent it.

## 5. Object 4: against the NY Fed's expectations/term-premium split

| 2026 to date | ACM fitted change | ACM expected rates | ACM term premium | Structural: US news | Global risk | Unspanned |
|---|---|---|---|---|---|---|
| 2-year | +135 | +99 | +36 | +65 | +10 | +61 |
| 5-year | +137 | +104 | +34 | +93 | +17 | +28 |
| 10-year | +109 | +86 | +23 | +101 | +22 | -12 |

**The two decompositions answer different questions:** ACM splits the *level* of a yield
into an expected short-rate path and a premium; the structural model labels each *day's
news* by its cross-asset signature. They agree on the 2026 headline: both read the 10-year
as mostly an expectations move, ACM through expected rates (79%) and the structural model
through US macro and monetary news (82% of the H.15 10-year's rise; 93% of ACM's fitted yield). The global-risk contribution (+22bp) is close in
size to ACM's term-premium rise (+23bp), as the safe-haven reading would imply; the
monthly co-movement between the two is too weak to call this more than suggestive.

**The pre-registered bridge did not hold up in 2026.** Projected on 2007-2025 data, the
cross-asset shocks load mainly on ACM's term premium (10-year: 2.7bp per US macro shock on
the premium against 1.4bp on expected rates). Carried into 2026, those loadings say US
news raised the 10-year term premium by about 72bp, when ACM's premium rose 23bp; the
shocks' fit to the premium collapses from 56% of monthly variance to 2%. Two of the three
stated expectations held in sample (global risk loads on the premium; US macro on both);
the third did not (monetary news loaded more on the premium than on expected rates).

**Exploratory explanation.** Monthly, the US-news component correlated 0.65 with ACM's
term premium and 0.43 with expected rates in 2007-2025; in 2026 0.49 and 0.86. In a sample
dominated by near-zero policy rates, good US news could not move the expected short-rate
path much and showed up in the premium; in 2026, with policy away from the lower bound,
the same news moves expected rates. This is the Swanson-Williams pattern of a lower bound
muting the response of rate expectations, and it means that any fixed mapping from
cross-asset news into an expectations/premium split is regime-dependent.

## 6. Explanatory fit and forecasting

**Explaining the day's move** (frozen loadings, daily $R^2$ and RMSE):

| | 2-year | 5-year | 10-year | 30-year |
|---|---|---|---|---|
| $R^2$ 2007-2025 (in sample) | 52% | 81% | 91% | 80% |
| $R^2$ 2026 (out of sample) | 59% | 83% | 92% | 80% |
| RMSE 2026, bp (daily s.d. 5.1/5.0/4.5/3.9) | 3.2 | 2.0 | 1.3 | 1.7 |

The structure is stable: loadings fixed in 2025 explain 2026 as well as they explained the
past. The weak spot is the front end.

**Forecasting the next move** (from the next close; out-of-sample $R^2$ against no change):

- **2012-2025, real time:** every model is below zero at every maturity and horizon. Own
  move: 0 to -6%; adding the curve state: -1% to -31% (mean reversion in levels that does
  not survive out of sample); adding the origin of today's news changes nothing (Clark-West
  p against the curve-state model 0.11-1.00). **The pre-registered rule fails for all four
  maturities: origin carries no forecasting information.**
- **2026, frozen model:** the same; the 2-year at 20 days is worst (-41%, the curve-state
  model betting on mean reversion during a sustained selloff).
- **One apparent exception is an artefact.** Measured from the same close, today's news
  "predicts" tomorrow's 10-year H.15 change ($R^2$ +1.3%, p < 0.001). The H.15 yields are
  recorded before the New York close, so tomorrow's H.15 change contains the end of today's
  move. It is not tradeable, and it disappears from the next close.

## 7. Caveats

- The H.15 yields are not recorded at the model's close; the two lags in the projection
  handle this for attribution. LSEG benchmark yields at the 2-, 5- and 30-year (`US2YT=RR`
  and so on) would remove it and are the natural upgrade.
- The identified sets are wide (US-news bands span 75-90bp). Robust statements concern
  origin (US against euro area against risk sentiment) and the unspanned front end, not
  the macro/monetary split.
- ACM's daily expected-rate and term-premium changes are themselves noisy (daily
  correlation -0.23), so daily comparisons with it are less informative than monthly ones.

## Deviations from pre-registration 15

| Change | Reason |
|---|---|
| Added a monthly comparison of the US-news component with ACM expected rates and term premium (section 5, figure 21 right) | The pre-registered daily bridge failed in 2026; the monthly comparison shows why. Labelled exploratory |
| Added same-close one-day forecasts beside the pre-registered next-close ones | To show the size of the H.15 recording-time artefact |
