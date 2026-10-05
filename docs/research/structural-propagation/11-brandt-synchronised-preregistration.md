# Addendum to pre-registration 08: the synchronised cross-Atlantic model

*Written on 5 October 2026, before the synchronised model is estimated. Everything not
stated here is exactly as in [08-brandt-and-2026-preregistration.md](08-brandt-and-2026-preregistration.md):
restrictions, lags, prior, draws, replication checks, propagation tests, decision rules,
freezing and the 2026 protocol. The free-data model frozen in `897dea3` is kept and
reported; this is an additional model, not a replacement.*

## Why

The free-data replication ([09-brandt-results.md](09-brandt-results.md)) showed that
European cash prices, recorded about five and a half hours before New York prices, catch
up the next day with US afternoon news. This understates spillovers on impact and creates
spurious next-day predictability. LSEG Workspace provides euro-area prices recorded at,
or close to, the New York close. Measured before this addendum on 1999-2025, the
coefficient of the next-day change on today's Treasury (or S&P 500) move is:

| Series | Next-day coefficient | Same-day correlation with the US series |
|---|---|---|
| Bundesbank 10-year zero (used so far) | 0.40 | 0.25 |
| 10-year EONIA/ESTR OIS composite (LSEG) | 0.07 | 0.64-0.68 |
| Euro Bund future, last trade (Eurex closes 22:00 Frankfurt) | 0.02 | 0.69 |
| Cash EURO STOXX index (17:30 Frankfurt) | 0.24 | 0.59 |
| Euro Stoxx 50 future, last trade | -0.05 | 0.77 |
| Euro-dollar mid price, 2007 onwards (identical to the Americas close) | 0.02 | 0.23 |

## Data

| Variable | Series |
|---|---|
| Euro-area 10-year rate | 10-year OIS: EONIA composite (`EUREON10Y=`, mid of bid and ask) to 31 December 2019, ESTR composite (`EUREST10Y=`) from 2 January 2020, spliced in levels at the switch. This is Brandt et al.'s own variable |
| Euro-area equity | Euro Stoxx 50 future, last trade (`STXEc1`), roll-adjusted: on the first trading day after each quarterly expiry (third Friday) the return is measured within one contract |
| US equity | S&P 500 (Yahoo; not in the Workspace entitlement) |
| Euro-dollar | `EUR=` mid price (the Americas close from 2007) |
| US 10-year | `US10YT=RR` benchmark mid yield |

**Sample:** 2 January 2007 to 31 December 2025, the period in which every series is
synchronised; all 18 of Brandt et al.'s events fall inside it. **Robustness:** the
Bund future's last trade, converted to a yield change with the benchmark's modified
duration, in place of the OIS rate.

## Expectations stated in advance

If timing explains the free-data gaps, the synchronised model should show (i) next-day
coefficients near zero in the lead-lag check, (ii) a US share of euro-area rate variance
on impact closer to the published 40%, and (iii) the close-to-close propagation tests
losing the spurious next-day predictability, so that they agree with the next-close
version.

## Licensing

LSEG data are cached locally and never committed; only derived results (estimated
models, summary tables, figures) enter the repository.
