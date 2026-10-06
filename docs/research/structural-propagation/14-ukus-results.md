# The UK-US model and the 2026 gilt selloff

*Pre-registration [13-ukus-preregistration.md](13-ukus-preregistration.md) (committed
`d6cf275` before estimation). Models frozen in `3e04261`: Model A SHA-256
`3282df3f...b4e2`, Model B `63d07fa9...6d75`. LSEG prices, 2007-2025; 2026 to
5 October. Tables: `reports/structural_propagation/ukus_{A,B}/` and
`application_2026/ukus_*`; figures 15-17.*

---

## Conclusion

1. **The 2026 gilt selloff was mostly imported, and it was not a fiscal-credibility
   event.** Of the 10-year gilt's 95bp rise in 2026 to date, US news and global risk
   sentiment account for 84bp in the like-for-like model (A) and 91bp in the model with
   a UK risk-premium shock (B). The risk-premium shock, the signature a fiscal scare
   leaves, contributes -7bp, with a 90% range of -17 to +42bp.
2. **There was a domestic component in the spring and summer, but of the
   sterling-strengthening kind.** Over 27 February to 19 August (+81bp), UK monetary
   news adds 22-35bp: a Bank of England repricing, in which gilt yields and sterling rise
   together. That is the opposite of the gilt-vigilante signature.
3. **The risk-premium extension earns its place.** Brandt et al.'s five shocks cannot
   represent a day on which gilts sell off while sterling falls, and Model A misreads
   the 2022 mini-budget as UK growth and policy news; Model B makes the risk premium the
   largest component of every day of that episode.
4. **On the research question, the UK agrees with the US and the euro area.** Apparent
   next-day predictability of gilts (4% of $R^2$) is the London-close catch-up; measured
   from the next close it disappears, and no model beats a no-change forecast.

---

## 1. Data and timing

No sterling rate is recorded at the New York close. Gilts close in London, so 16% of a
day's Treasury move reaches gilts the next day (t = 9.7), against 39% for the Bundesbank
curve and 0-8% for the synchronised euro-area series. Sterling (the Americas close) and
the FTSE 100 future (last trade at 21:00 London) are synchronised. The sterling OIS
composite was too stale to use. Two consequences: the 2026 decompositions run through
each VAR's dynamics, which credits the next-day catch-up to the shock that caused it; and
one-day propagation tests are read only in their next-close form.

## 2. What the models say about 2007-2025

**Variance shares on impact** (mean over admissible draws):

| Share of daily variance | Model A: UK / US / global | Model B: UK / US / global |
|---|---|---|
| 10-year gilt | 66 / 27 / 7% | 70 / 20 / 10% |
| UK equity | 39 / 40 / 21% | 43 / 33 / 24% |
| US equity | 30 / 44 / 26% | 38 / 34 / 28% |
| Sterling | 18 / 40 / 41% | 47 / 30 / 23% |

Gilts are more domestically driven than euro-area rates (US share 20-27% against 35-40%),
and over two-day changes the US share barely rises (28%), so this is not a timing effect.
In Model B the UK risk-premium shock alone explains 17% of daily gilt variance and 17%
of sterling's, as much as UK monetary or UK macro news.

**Validation events.**

- **Model A** attributes 6 of the 9 events it can represent as expected (median-target
  model; 45% of admissible draws on average). It reads the mini-budget days as UK macro
  and UK monetary news, because it has nothing else to put them in.
- **Model B** makes the UK risk premium the largest component of the mini-budget
  (+40bp of +75), the rout that followed (+31 of +68), the Bank's gilt purchases (-29 of
  -36) and the reversal (-26 of -38). It reads Brexit as UK monetary easing plus a global
  risk-off. The cost: it attributes several monetary-policy days (the 2008 LSAP, the 2013
  taper tantrum, the 2020 emergency cut, the 2021 and 2023 hikes) to other shocks, so its
  overall hit rate is lower (6 of 12; 37% of draws).

The two models are complements: A for policy days, B for days on which sterling and gilts
part company.

**Propagation.** Close to close, cross-asset news adds 4.4% of $R^2$ for the next day's
gilt move and the US-origin part of a gilt move "continues" the next day. That is the
London-close catch-up. Measured from the next close, the identification-free test is
insignificant at every horizon (p = 0.15-0.95, incremental $R^2$ at most 0.3%), the
origin split adds nothing, and no model beats a no-change forecast in real time.

## 3. The 2026 gilt selloff

| 10-year gilt | Actual | Main contributions, bp (90% of identified set) |
|---|---|---|
| Model A, 27 Feb-19 Aug | +81 | UK monetary +35 [-7, 73], global risk +25 [-1, 41], US monetary +15, US macro +9, UK macro +1 |
| Model B, 27 Feb-19 Aug | +81 | US macro +30 [-4, 55], UK monetary +22 [-8, 66], global risk +14, **UK risk premium +9 [-12, 41]**, UK macro +8, US monetary +3 |
| Model A, 2026 to date | +95 | US monetary +45 [1, 76], global risk +29 [1, 54], UK monetary +11, US macro +10, UK macro +6 |
| Model B, 2026 to date | +95 | US monetary +39, US macro +29, global risk +23, UK monetary +8, UK macro +8, **UK risk premium -7 [-17, 42]** |

The 2-year gilt (Model B) rose 114bp in 2026 to date, of which US monetary and macro news
+88bp and UK macro news +32bp: the front end imported the repricing of US policy and
added a UK growth component.

**Reading.** A global (largely US) repricing of rates, plus improving risk sentiment that
eroded the safe-haven bid for gilts, carried most of the 2026 move. The UK-specific part
came in the spring and summer as Bank of England repricing that lifted gilts and sterling
together. The pattern that would indicate a fiscal-credibility premium, gilts rising
relative to Treasuries while sterling falls, is close to absent: the risk-premium
contribution is small in the window and negative over the year, consistent with the
August descriptive finding that sterling was flat and the gilt-OIS spread unchanged.

**Caveats.** The identified sets are wide (most bands span 50bp or more), so the robust
statements are about origin (imported versus domestic) and about the sign of the
risk-premium contribution, not about the precise split within US news. The risk-premium
shock also captures UK-specific inflation-risk repricing; with these prices the two
cannot be separated, which strengthens the conclusion (neither moved gilts much) rather
than weakening it.

**Propagation in 2026:** no model beats a no-change forecast of gilts; the largest
one-day gain (+1.2% $R^2$) is the London-close catch-up.
