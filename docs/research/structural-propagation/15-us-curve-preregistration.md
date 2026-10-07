# Pre-registration: the US Treasury curve through the cross-Atlantic model (Model A)

*Written on 7 October 2026, before any 2026 observation of the 2-, 5- or 30-year Treasury
or of the NY Fed's daily term-structure decomposition is passed through the model.
Requested by the owner: "build the best defensible US Brandt replication (Model A only,
shelve Model B), freeze the specification, and apply it to the 2026 US bond market
selloff". Unless stated, every choice is as in pre-registrations 08 and 11.*

## 1. Question

What drove the 2026 rise in Treasury yields at the 2-, 5-, 10- and 30-year maturities,
when the drivers are identified from cross-asset co-movement (Brandt et al., 2021)
rather than from the yield curve alone? When did the dominant driver change, what
separates the front end from the long end, and does the structural attribution agree
with an independent expectations/term-premium decomposition?

## 2. The model: Model A, frozen, not re-estimated

**Model A is the synchronised cross-Atlantic model frozen in `ee532fe`** (SHA-256
`4b204619...79d489`): Brandt et al.'s five variables and five shocks (euro-area
monetary, euro-area macro, US monetary, US macro, global risk), their Table 1 sign
restrictions, LSEG prices recorded at or near the New York close, 10-year EONIA/ESTR OIS
as the euro-area rate, 2007-2025, four lags, Minnesota tightness 0.2, 1,000 admissible
draws.

Why this and not an alternative:

- It is Brandt et al.'s own specification on their own euro-area rate variable, and the
  only one of our versions whose timing is synchronised.
- It was frozen before any 2026 data were used, so it cannot have been tuned to 2026.
- Its replication record: US share of euro-area rate variance 35% (paper: about 40%),
  equity spillovers in both directions as published, median-target model attributes 15
  of the paper's 18 events as expected (50% of admissible draws on average).
- The Bund-future variant matches the published rate spillover more closely (40%) but
  its median-target model attributes only 4 of 18 events as expected; it is not used.
- **Model B (an added home risk-premium shock) is shelved.** It was built for the UK,
  where the question was a fiscal-credibility premium; no US analogue is estimated.

## 3. Extension to the Treasury curve (fixed now, estimated on 2007-2025 only)

The model contains one Treasury yield, the 10-year (the euro-area rate minus the
spread). Other maturities are attached by projection, which leaves the identification
untouched:

$$\Delta y_{\tau,t} = c_\tau + \sum_{k=1}^{5}\sum_{s=0}^{2}\theta_{\tau,k,s}\,\varepsilon_{k,t-s} + u_{\tau,t},$$

estimated by OLS on 2007-2025, separately for each of the 1,000 admissible draws (each
draw has its own shocks $\varepsilon$ and therefore its own loadings $\theta$). The
contribution of shock $k$ to a window's change is
$\sum_t\sum_s\theta_{\tau,k,s}\varepsilon_{k,t-s}$; the remainder (intercept and
$u_{\tau,t}$) is reported as **unspanned**: curve-specific news that the five
cross-asset shocks do not represent.

- **Yields:** FRED H.15 constant-maturity Treasury yields at 2, 5, 10 and 30 years
  (`DGS2`, `DGS5`, `DGS10`, `DGS30`). All four tenors use the same source so that the
  cross-section is like for like; the 10-year therefore also enters by projection.
- **Why two lags.** The H.15 yields are recorded earlier in the New York afternoon than
  the model's prices. Measured on 2007-2025 before this note: the daily change in the
  H.15 10-year correlates 0.95 with the LSEG benchmark the model uses, and the next-day
  H.15 change loads on today's LSEG move (0.04 at 2 years, 0.18 at 5, 0.51 at 10, 0.25
  at 30, all controlling for the own lag). Lags 1 and 2 credit that catch-up to the
  shock that caused it, as the VAR dynamics did in documents 10 and 12.
- **Point estimate and bands:** the median-target draw for charts; 5-95% across the
  1,000 draws as "90% of the identified set".

The loadings are saved with their SHA-256 and committed before any 2026 tenor data are
read.

## 4. The four objects

1. **Cumulative 2026 decomposition** of the 2-, 5-, 10- and 30-year yields by shock,
   over 2026 to date and over 27 February-19 August 2026.
2. **Time-varying decomposition.** Cumulative daily contributions through 2026; the
   dominant shock in each calendar month and in rolling 20-day windows (largest absolute
   contribution to the window's change), with the share of draws agreeing. A change in
   the dominant driver is dated where the rolling-window leader changes and keeps the
   lead for at least 10 trading days.
3. **Cross-section of the curve.** Contributions by maturity; the 2s10s and 10s30s
   slopes decomposed the same way; and each shock's curve signature (the 2007-2025 impact
   loading by maturity, bp per one-standard-deviation shock).
4. **Structural versus expectations/term-premium attribution.** The NY Fed's daily ACM
   decomposition at 2, 5 and 10 years (fitted yield = risk-neutral yield + term premium),
   an identification that uses only the yield curve. Two comparisons:
   - cumulative 2026 changes in the risk-neutral yield and in the term premium beside the
     structural decomposition of the same maturity;
   - a bridge: the risk-neutral yield and the term premium are each projected on the five
     shocks (Section 3's equation, 2007-2025), and their 2026 changes decomposed by shock.
   There is no published ACM counterpart at 30 years, so object 4 stops at 10 years.

**Expectations stated in advance:** monetary shocks load mainly on the risk-neutral
yield and most at the front end; the global-risk shock loads mainly on the term premium
(risk-off lowers it); US macro news loads on both.

## 5. Explanatory fit and forecasting

**Explanatory fit (contemporaneous):** $R^2$ and RMSE of the fitted daily (and
non-overlapping 5-day) tenor changes, in-sample 2007-2025 and out of sample in 2026 with
the frozen loadings. This measures how much of each maturity the structure accounts
for, not whether it predicts.

**Forecasting (the negative result to confirm or overturn).** Outcomes: the change in
each tenor over 1, 5 and 20 trading days, starting at the next close (the catch-up
documented in Section 3 is not a tradeable signal). Models: M0 no change; M1 the day's
own move; M2 plus curve state (2-, 10- and 30-year levels, the tenor's 20-day change and
volatility); M3 plus the US, euro-area and global parts of the day's move; M4 plus all
five VAR innovations (identification-free upper bound). Real time, expanding window,
2012-2025: the VAR, identification (200 draws) and loadings are re-estimated each year
on data before it. 2026: the frozen model and loadings, regressions estimated through
2025. Reported: out-of-sample $R^2$ against no change, RMSE (bp), and Clark-West tests of
M3 and M4 against M2. **Decision rule:** origin carries forecasting information for a
maturity if M3 beats M2 (Clark-West p < 0.05) at two or more horizons in 2012-2025 and
its $R^2$ against no change is positive at those horizons.

## 6. Disclosure

Already known about 2026: documents 10 and 12 decomposed the 10-year Treasury (LSEG
benchmark, through the VAR) and the 2-year (through the Cieslak-Pang US model); the
August descriptive work reported the published ACM 10-year split over 27 February-19
August (+51bp expected rates, +17bp term premium). Nothing about the 5- or 30-year, or
about the 2-year through this model, has been computed.

## 7. Deviations log

| Date | Change | Reason |
|---|---|---|
| (none yet) | | |
