# The cross-Atlantic model: replication and propagation

*Brandt, Saint Guilhem, Schröder and Van Robays (2021, ECB WP 2560) on free data,
1999-2025, under [08-brandt-and-2026-preregistration.md](08-brandt-and-2026-preregistration.md)
(committed `26bd4d4` before estimation; model frozen in `897dea3`, SHA-256
`2fd02b43...e345ae`). Tables: `reports/structural_propagation/brandt/`; figures 7 and 8.*

---

## Conclusion

1. **The replication works once a timing problem is recognised.** European prices are
   recorded at the European close, about five and a half hours before US prices, so US
   news from the New York afternoon reaches the Bund only the next day. On daily
   close-to-close data this halves the measured Bund-Treasury co-movement and
   understates US spillovers on impact. Measured over two days or a week, the
   spillovers come close to the published ones.
2. **The same timing problem produces spectacular but spurious "propagation".** On
   close-to-close data, today's cross-asset news "predicts" 28% of tomorrow's Bund
   move, and a real-time model earns an out-of-sample $R^2$ of +27% at one day. That
   is the European market catching up overnight with US news, not the propagation of
   structural shocks. It is a measurement artefact, and it cannot be traded at the
   recorded prices.
3. **With the catch-up removed, the cross-Atlantic model gives the same answer as the
   US model.** Origin carries a statistically detectable but economically negligible
   amount of information, a random split of the same news does as well, and nothing
   beats a no-change forecast in real time.

---

## 1. Replication

**Spillover shares** (one-step-ahead variance shares, averaged over admissible draws as
in the paper; 1999-2023, the paper's sample):

| Share of daily variance | Euro-area shocks | US shocks | Global risk | Brandt et al. |
|---|---|---|---|---|
| Bund 10-year (paper: 10-year OIS) | 68% | 26% | 7% | US shocks close to 40% |
| Euro-area equity | 42% | 39% | 19% | US close to 40%; foreign more than half |
| US equity | 32% | 48% | 20% | Euro-area shocks about 30% |
| Euro-dollar rate | 16% | 49% | 35% | Euro area about 20%, US about 40%, global risk dominant |

Equity spillovers in both directions match. The two misses are the US share of the
euro-area rate (26% against about 40%) and the global-risk share of the exchange rate
(35%, not dominant).

**Why the rate spillover is low: timing, not economics.**

- Today's change in the US 10-year predicts tomorrow's Bund change with a coefficient of
  0.40 (t = 36, $R^2$ = 25%); the reverse coefficient is -0.03. Forty per cent of a
  day's Treasury move reaches the Bund the next day and nothing flows back.
- The daily Bund-Treasury correlation is 0.25; over non-overlapping two-day changes
  0.50, over weekly changes 0.64.
- Re-estimated on two-day and weekly changes, the US share of Bund variance rises from
  27% (daily, 1999-2025) to 34% and 35%, close to the published 40%. Equity spillovers
  are unchanged.

The remaining gap is plausibly the data substitution: the Bund carries euro-area
safe-haven and sovereign-stress premia that the OIS rate does not, which makes it look
more domestically driven.

**Event study** (their Table 2: the two-day change in the euro-area rate around 18
dated events, each with the shock the authors expect to dominate). The median-target
model attributes 13 of the 18 events as expected; on average 48% of admissible models
do. Four of the five misses are announcements made after the European close (the 2009
and 2010 FOMC asset-purchase decisions, the 2016 US election result, which came
overnight, and the PEPP announcement late in the evening), so the two markets react on
different recorded days: the same timing problem.

**Global risk.** The global-risk shock co-moves with daily VIX changes (median
correlation 0.29; 90% of admissible models between 0.05 and 0.60) but barely with the
MOVE index of Treasury volatility (0.04). That fits the identification: the shock is
defined by equities and the dollar as a safe haven, not by rate volatility.

## 2. Propagation

The pre-registered tests, with origin (domestic, foreign, global) in place of the
expectations/premium split.

**Close-to-close, as pre-registered: an artefact.** For the Bund, the other day-$t$
innovations add 28% of $R^2$ for the next day's change; the foreign and global parts of
today's move "continue" strongly; in real time over 2004-2025 the full cross-asset
model earns +27% out-of-sample $R^2$ at one day and +2.7% at five days (Clark-West
p < 0.001). Under the letter of the pre-registered rule, the null is rejected. It is
not economically interpretable: the predictable part is the next-day catch-up of the
European close to US afternoon prices, which nobody can trade at the recorded prices.

**From the next close (the catch-up removed):**

| Bund 10-year, change from day $t+1$ to $t+h$ | h = 2 | h = 5 | h = 10 | h = 20 |
|---|---|---|---|---|
| Identification-free test, p-value | 0.03 | 0.03 | 0.03 | 0.22 |
| Incremental $R^2$ | 0.29% | 0.33% | 0.22% | 0.10% |
| Origin split beats random splits (share of draws) | 3% | 0% | 3% | 9% |
| Real time, all cross-asset news vs curve state (Clark-West p) | 0.04 | 0.07 | 0.29 | 0.98 |

Cross-asset news has the same small predictive content for the Bund as it had for
Treasuries, the origin labels add nothing over random splits (at most 13% of draws for
any outcome), and nothing beats a no-change forecast in real time.

**Verdict.** On the timing-robust version of the pre-registered rule, the null is not
rejected for the Bund (real-time significance at one horizon only), and the
identification carries no incremental predictive information. Both models now point
the same way: structural origin attributes moves credibly but does not predict them.

## 3. Deviations and what they mean

Recorded in the deviations log of pre-registration 08. The next-close tests,
multi-horizon variance shares and lower-frequency re-estimation were added after the
timing problem appeared in the first estimates; they are reported beside, not instead
of, the pre-registered close-to-close results. A faithful daily replication needs
synchronised prices: euro-area rates and equities sampled at the New York close (for
instance from Refinitiv or Bloomberg), or both markets at a common London time.
