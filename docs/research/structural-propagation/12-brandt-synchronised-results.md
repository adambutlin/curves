# The synchronised cross-Atlantic model

*LSEG prices recorded at or near the New York close, 2007-2025, under
[11-brandt-synchronised-preregistration.md](11-brandt-synchronised-preregistration.md)
(committed `a88caf7` before estimation; model frozen in `ee532fe`, SHA-256
`4b204619...79d489`). LSEG data stay local; tables in
`reports/structural_propagation/brandt_sync/` (OIS rate) and `brandt_sync_bf/` (Bund
future); figures 12-14.*

---

## Conclusion

1. **Synchronising the data turns a partial replication into a close one.** With
   euro-area prices recorded at the New York close, the overnight catch-up vanishes,
   same-day Bund-Treasury co-movement more than doubles, and the US share of euro-area
   rate variance rises from 27% to 35% (OIS) and 40% (Bund future), against the
   published 40%. The other spillovers match the paper.
2. **The answer to the research question does not change.** On synchronised data the
   spurious next-day "predictability" of euro-area rates falls from 28% of $R^2$ to
   0.5%. What remains is statistically detectable (by the letter of the pre-registered
   rule the identification-free null is now rejected for the euro-area rate) but
   economically negligible: no model beats a no-change forecast in real time, and the
   origin labels add nothing over random splits.
3. **For 2026 the synchronised model corrects the free-data story.** The euro-area
   10-year rate's rise was imported from the US; the euro-area monetary contribution
   that the free-data model found was largely the overnight catch-up misread as
   domestic news (Section 3, and [10-2026-application.md](10-2026-application.md)).

---

## 1. Replication

**Timing (common 2007-2025 sample):**

| Data | Next-day euro-area rate on today's Treasury | Same-day correlation, rates | Same-day correlation, equities |
|---|---|---|---|
| Free data (European closes) | 0.39 (t = 28.5) | 0.27 | 0.61 |
| LSEG OIS (near the NY close) | 0.08 (t = 5.6) | 0.61 | 0.86 |
| LSEG Bund future (NY close) | 0.00 (t = 0.0) | 0.76 | 0.86 |

**Spillover shares** (one-step-ahead variance shares, mean over admissible draws,
2007-2025):

| | Free data | Synchronised, OIS | Synchronised, Bund future | Brandt et al. |
|---|---|---|---|---|
| US shocks in the euro-area rate | 27% | 35% | 40% | close to 40% |
| US shocks in euro-area equity | 37% | 38% | 36% | close to 40% |
| Euro-area shocks in US equity | 28% | 33% | 35% | about 30% |
| Euro-dollar: euro area / US / global risk | 19 / 39 / 43% | 25 / 40 / 36% | 30 / 40 / 30% | about 20 / about 40 / dominant |

Two-day variance shares now equal the one-day shares: no shock's effect arrives late.
The global-risk shock co-moves more with VIX (median correlation 0.34, from 0.29); it
still barely moves with MOVE (0.05), as expected for a shock defined by equities and the
dollar's safe-haven role.

**Event study.** On average across admissible models, half of Brandt et al.'s 18
events are attributed to the expected shock (50% with the OIS rate, 53% with the Bund
future). The single median-target model scores 15 of 18 with the OIS rate but only 4 of
18 with the Bund future: one representative draw is a fragile summary of a set
identification, which is why the cross-draw average is the statistic to read.

## 2. Propagation on synchronised data

| Euro-area 10-year rate, next day | Free data | Synchronised, OIS | Synchronised, Bund future |
|---|---|---|---|
| Incremental $R^2$ of other news (identification-free) | 28.3% | 2.6% | 0.5% |
| Origin split beats random splits (share of draws) | 38% | 10% | 1% |
| Real-time $R^2$ vs no change, all cross-asset news | +27% | +0.2% | -1.0% |

The residual next-day effect in the OIS version (2.6%) shrinks to 0.5% with the fully
synchronised Bund future: it is mostly the remaining gap between the OIS composite's
snapshot and the New York close, a measurement issue.

**Pre-registered decision rules, Bund future (cleanest timing):** the identification-free
test rejects at 1, 5 and 10 days (p = 0.006, 0.006, 0.045), and the full-news model
improves on the curve-state model in real time at 1 and 5 days (Clark-West p = 0.0006,
0.013). By the letter of the rule, the null that origin is irrelevant is rejected for the
euro-area rate. But the improvement is relative to a curve-state model that is itself
worse than no change: every model's out-of-sample $R^2$ against a no-change forecast is
negative. The identification criterion fails: the origin split beats random splits in at
most 4% of draws for the euro-area rate and improves real-time forecasts at one horizon
only. Economic reading: cross-asset news contains a sliver of statistically detectable
information about next-week euro-area rates, of the same size as in Treasuries
(0.1-0.7% of $R^2$), and the structural labels are not where it lives.

## 3. 2026 through the synchronised model

27 February to 19 August 2026 (90% of the identified set in brackets):

| | Actual | Contributions (bp) |
|---|---|---|
| Euro-area 10-year OIS | +57 | US macro +33 [0, 50], euro-area macro +13 [-2, 40], global risk +5, US monetary +5, euro-area monetary +3 [-5, 36] |
| 10-year Treasury | +69 | US macro +52 [2, 62], global risk +14, US monetary +6 |

2026 to date (to 5 October): the euro-area 10-year OIS rose 66bp, of which US macro news
+44 [0, 62] and US monetary news +23 [2, 59], with euro-area news -7; the Treasury rose
118bp, of which US macro +69 [3, 88], US monetary +31 [4, 84], global risk +23.

**What changed against the free-data model.** The free-data model gave euro-area monetary
news +21bp of the Bund's selloff-window rise; the synchronised model gives it +3bp. A Bund
move on the morning after a US afternoon selloff, with no same-day US move, is exactly
what a domestic euro-area shock looks like on unsynchronised data. The free-data finding
was therefore largely a measurement error, not economics. Within the US contribution the
synchronised model also shifts weight from monetary to macro news; that split is not
robust across models, while the US origin is.

**Propagation in 2026:** no model beats a no-change forecast of the euro-area rate or
the Treasury in 2026 (as planned, too few days to test propagation).
