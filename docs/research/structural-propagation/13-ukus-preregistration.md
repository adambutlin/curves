# Pre-registration: the UK-US model and the 2026 gilt selloff

*Written on 6 October 2026, before either UK model is estimated. Approved by the owner
("build the same synchronised model for UK gilts against the US"). Unless stated, every
choice is as in [08-brandt-and-2026-preregistration.md](08-brandt-and-2026-preregistration.md)
and [11-brandt-synchronised-preregistration.md](11-brandt-synchronised-preregistration.md).*

## 1. Question

Was the 2026 gilt selloff domestic or imported? And if domestic, was it UK policy or
growth news (which strengthens sterling) or a rise in the compensation investors demand
for holding UK assets (which weakens it)?

## 2. Two models

**Model A, like-for-like:** Brandt et al.'s five shocks with the UK in place of the euro
area: UK monetary, UK macro, US monetary, US macro, global risk. Variables: the 10-year
gilt yield, UK equity, US equity, the dollar price of sterling, and the UK minus US
10-year spread. Restrictions exactly as their Table 1.

**Model B, with a UK risk-premium shock.** Model A cannot represent a day on which gilt
yields rise relative to Treasuries while sterling falls: in Brandt et al.'s table every
domestic shock strengthens the home currency. That signature is what a fiscal-credibility
scare (the September 2022 mini-budget) or a UK-specific inflation-risk repricing looks
like. Model B adds the 2-year gilt yield as a sixth variable and a sixth shock:

| Shock (positive) | UK 2y | UK 10y | UK equity | US equity | Sterling | UK minus US 10y |
|---|---|---|---|---|---|---|
| UK monetary | + | + | - | | + | + |
| UK macro | + | + | + | | + | + |
| **UK risk premium** | | + | | | **-** | + |
| US monetary | | + | | - | - | - |
| US macro | | + | | + | - | - |
| Global risk | | - | - | - | - | + |

The six sets are mutually exclusive up to sign. The risk-premium shock is a *label for a
signature*: it captures fiscal-credibility shocks and UK-specific inflation-risk
repricing alike, which cannot be separated with these prices.

## 3. Data (LSEG, recorded as late as available; synchronisation measured before this note)

| Variable | Series | Next-day coefficient on today's US move |
|---|---|---|
| UK 10-year and 2-year | `GB10YT=RR`, `GB2YT=RR` benchmark mid yields | 0.16 (10-year): gilts close in London |
| UK equity | FTSE 100 future, last trade (21:00 London), roll-adjusted | -0.12 |
| Sterling | `GBP=` mid (the Americas close) | 0.03 |
| US 10-year, US equity | `US10YT=RR`; S&P 500 (Yahoo) | (reference) |

No sterling rate is recorded at the New York close: gilts and the Long Gilt future close
in London, and the SONIA OIS composite is too stale to use (same-day correlation with
Treasuries 0.10). The residual mismatch (0.16, against 0.39 for the free-data Bund) is
handled by (i) decomposing 2026 through the VAR's dynamics, which credits next-day
catch-up to the originating shock, and (ii) a robustness check on non-overlapping
two-day changes. **Sample:** 2 January 2007 to 31 December 2025. Four lags, Minnesota
tightness 0.2, 1,000 accepted draws, seed 20261010.

## 4. Validation events (expected dominant shock for the two-day gilt move)

| Date | Event | Expected |
|---|---|---|
| 2008-11-25 | Fed LSAP1 | US monetary |
| 2013-06-19 | Taper tantrum FOMC | US monetary |
| 2016-06-24 | Brexit referendum result | UK macro or global risk |
| 2016-08-04 | BoE package (cut, QE) | UK monetary |
| 2017-11-02 | BoE first hike since 2007 | UK monetary |
| 2020-03-19 | BoE emergency cut and QE | UK monetary |
| 2021-12-16 | BoE surprise hike | UK monetary |
| 2022-09-23 | Mini-budget | UK risk premium (Model B only) |
| 2022-09-26 | Gilt and sterling rout continues | UK risk premium (Model B only) |
| 2022-09-28 | BoE gilt purchases | UK risk premium or UK monetary |
| 2022-10-17 | Mini-budget reversed | UK risk premium (Model B only) |
| 2023-06-22 | BoE 50bp hike | UK monetary |

## 5. Tests and the 2026 application

Propagation tests and real-time evaluation exactly as in pre-registration 08, with the
gilt 10-year as the primary outcome and origin groups UK (Model B: UK monetary, macro and
risk premium), US and global. Both models are frozen at end-2025 (SHA-256 recorded)
before any 2026 observation is used; 2026 windows as before (2026 to date; 27 February to
19 August), decomposed through each VAR's dynamics, 90% of the identified set reported.

## 6. Prior beliefs, stated in advance

The August 2026 descriptive work found sterling flat, the gilt-OIS spread unchanged and
the UK 10-year rising by about as much as the US 10-year (77bp against 68bp from
27 February to 19 August). If those facts hold, Model B should attribute little of the
gilt selloff to the UK risk-premium shock and most of it to US and global news.

## 7. Deviations log

| Date | Change | Reason |
|---|---|---|
| (none yet) | | |
