# 2026 UK Gilt Selloff — Expectations or Term Premium? Design Spec

**Date:** 2026-08-20
**Status:** Approved (brainstorming), pending implementation-plan
**Branch:** `gilt-selloff-2026`
**Extends:** existing `giltcurve` package (Objectives 1–6 complete: SONIA OIS
ingest, bootstrap, forwards, implied Bank Rate path, PCA, ACM term premium
validated against the NY Fed published series).

---

## 1. Objective

Not to improve ACM. To use the frozen estimator plus observable market evidence
to answer a live investment question:

> What drove the 2026 UK gilt selloff associated with the energy/geopolitical
> shock, is the repricing economically justified, and does it create a trade?

Deliverable is a defensible 90-second macro trade pitch backed by reproducible
analysis.

## 2. The epistemic contract

Three categories, maintained everywhere, enforced structurally (§7):

- **OBSERVED** — gilt yields, SONIA/OIS, breakevens, Bund/UST yields, energy
  prices, GBP, issuance.
- **MODEL-IMPLIED** — ACM expected-rate component, ACM term premium. Latent.
- **INTERPRETATION** — inflation persistence, fiscal risk, duration supply, risk
  aversion, liquidity, positioning.

ACM gives a model-implied latent decomposition. It does **not** causally identify
why the term premium moved. No interpretation may ever be presented as something
ACM identified.

## 3. Evidence already established (2026-08-20, pre-implementation)

All figures pulled live during design from free public sources. They are recorded
here so the implementation has a regression target: if the pipeline reproduces
these, it is wired correctly.

### 3.1 OBSERVED — cumulative 27 Feb 2026 → 19 Aug 2026, basis points

| | 2y | 5y | 10y | 30y |
|---|---|---|---|---|
| UK gilt (BoE nominal) | +86 | +84 | **+77** | +74 |
| US Treasury (GSW) | +73 | +84 | **+68** | +55 |
| German Bund (BBSIS) | +81 | +70 | **+57** | +45 |
| UK SONIA OIS (BoE) | +93 | +85 | +75 | — |
| UK RPI breakeven (BoE) | — | +43 | +19 | +8 |

Brent 71.32 → 95.29 (+34%), **having peaked at $138.21 on 7 Apr and given back
~60% of the move since**. GBPUSD 1.3455 → 1.3556 (sterling flat). US 10y
breakeven (T10YIE) +5bp. 10y gilt–OIS spread +47 → +49bp (essentially unchanged).

The energy premium is unwinding while gilt yields sit at their highs. That
divergence is a load-bearing fact for the pitch, and W7 must be read against it.

### 3.2 MODEL-IMPLIED — same window, existing frozen ACM on refreshed data

| | Δy | ΔE[r] | ΔTP |
|---|---|---|---|
| UK 10y (our ACM) | +77 | +61 | +14 |
| US 10y (NY Fed published daily ACM) | +68 | +51 | +17 |

Two independent estimators — one ours, one third-party published — agree that the
move is expectations-dominated.

### 3.3 MODEL-IMPLIED — ACM behaviour across economically different episodes

Run on the frozen estimator during design. This is the interpretive key for what
the residual means, not a research contribution.

| Episode | 10y Δy | ΔE[r] | ΔTP |
|---|---|---|---|
| LDI, 22 Sep → 12 Oct 2022 | +99 | +40 | **+57** |
| COVID, 6 → 18 Mar 2020 | +61 | +15 | **+44** |
| MPC, 3 → 4 Nov 2021 | −12 | **−15** | +4 |
| CPI, 16 → 17 Aug 2022 | +14 | **+17** | −3 |

Dysfunction/funding events land in term premium; policy-news events land in
expected rates. The decomposition behaves sensibly before it is pointed at 2026.

**Known wrinkle, must be reported:** the first LDI week (22 → 27 Sep 2022) comes
out ΔE[r] +70 / ΔTP +17 — ACM assigns the initial mini-Budget shock mostly to
expectations, and term premium only builds over the following fortnight. This is
direct evidence for PM attack #1 (§10) and must appear in the note rather than
being suppressed.

### 3.4 Verified chronology

| Date | Event | Type |
|---|---|---|
| 2 Mar 2026 | IRGC announces Strait of Hormuz closure to US/Israel-allied shipping | escalation |
| 3 Mar 2026 | **Spring Statement + OBR forecast** — confounds the onset window | fiscal |
| early Mar 2026 | QatarEnergy force majeure after Ras Laffan strikes (~17% of capacity, 3–5yr repair) | energy |
| 12 Mar 2026 | Brent breaks $100 | energy |
| 7 Apr 2026 | **Brent peaks at $138.21** | energy |
| 19 Mar 2026 | MPC hawkish hold at 3.75%, unanimous (meeting ended 18 Mar) | policy |
| 8 Apr 2026 | Pakistan-brokered ceasefire, limited reopening | de-escalation |
| 18 Apr 2026 | Iran formally re-closes the strait | escalation |
| 23 Apr 2026 | DMO financing remit revision 2026-27 | supply |
| 17 Jun 2026 | US–Iran MOU to halt military operations | de-escalation |
| Jul 2026 | MOU collapses; Iran targets commercial shipping | escalation |
| 30 Jul 2026 | MPC holds 3.75%, **6–3, three votes to hike** (meeting ended 29 Jul) | policy |
| 19 Aug 2026 | CPI 2.9% (from 2.6%), **services 3.4% (down from 3.6%)** | macro |
| 17 Sep 2026 | MPC annual QT review — next 12-month gilt reduction announced | forthcoming |
| Autumn 2026 | Autumn Budget, the year's main fiscal event; OBR assesses fiscal rules | forthcoming |

Two confounds are structural and are handled in §8: the Spring Statement sits on
the onset window, and the DMO remit revision sits inside the long-end leg.

### 3.5 Interpretation forming (label: INTERPRETATION)

Consensus commentary attributes the selloff to gilt vigilantes and a UK fiscal
risk premium. The observable evidence is in tension with that: ~75–90% of the UK
move is matched by US and German duration, sterling is flat, and the gilt–OIS
spread is unchanged at 10y. The UK-specific residual is +9bp vs the US and +20bp
vs Bunds at 10y. DMO has already cut long conventional issuance to 3.2% of the
2026-27 programme. This is the disagreement the pitch will express.

### 3.6 Prior work located

NIESR term-premium tracker (~100bp 10y; our level ~130bp, same family), IFS on
the Budget and bond markets, Goldman Sachs "Why Are UK Gilt Yields So High",
J.P. Morgan "the sell-off has gone too far", Allocation Strategy (Aug 2026) on
gilt expected returns. None runs a UK ACM event study against a matched global
control with pre-specified windows. That is the gap this fills.

## 4. Frozen — do not modify

`premium/acm.py`, `premium/pca.py`, `premium/panel.py`, `curves/discount.py`,
`curves/ois_bootstrap.py`, `curves/forwards.py`, `conventions.py`.

The estimator ran clean on data refreshed to 19 Aug 2026 and reproduced sensible
behaviour on four historical episodes. There is no correctness problem to fix.

## 5. Required fix

`policy/mpc.py` — the 2026–27 announcement dates are projected from BoE cadence
and are demonstrably wrong: the constant says 6 Aug 2026, the actual meeting
ended 29 Jul 2026. Reconcile the full 2026 and 2027 list against the BoE
published calendar before Step 3 (meeting-dated corroboration) runs. The module
docstring already flags the list as needing verification; this closes it.

## 6. Module layout

```
src/giltcurve/
  ingest/
    boe_curves.py     NEW  generalise boe_gilt.py to all four BoE daily
                           archives (nominal / real / inflation / OIS) with
                           `kind` as a parameter. boe_gilt.py already carries
                           the parse mechanics and the two live-site quirks
                           (flat-vs-nested zip, spot-sheet rename); this lifts
                           them once instead of four times.
    bundesbank.py     NEW  BBSIS daily Svensson zero yields (1/2/5/10/30y)
    fred.py           NEW  fredgraph CSV: Brent, GBPUSD, DGS10/30, T10YIE
    dmo.py            NEW  gilt operations results, gilts in issue, net issuance
    fed.py            EDIT add `ACM Daily` sheet reader (the workbook is already
                           downloaded; only the monthly sheet is currently used)
  episode/
    chronology.py     NEW  event dates as a versioned constant + window builder
    eventstudy.py     NEW  Δy = ΔE[r] + ΔTP per (window, tenor); cross-market
                           matched-maturity differentials; placebo distribution
    supply.py         NEW  net DV01 supplied to private investors
scripts/
  run_episode.py      NEW  produces every figure and table in one pass
docs/notes/
  2026-gilt-selloff.md NEW research note + 90-second pitch
```

`boe_curves.py` supersedes `boe_gilt.py`; the latter's public functions are
re-exported from it so `scripts/run_term_premium.py` and the existing tests keep
working unchanged. This is a targeted improvement to code the work sits directly
on top of, not opportunistic refactoring.

The `ACM Daily` addition to `fed.py` is the single highest-value line in the
design: it yields a published, third-party, daily US decomposition as an
independent second estimator, for free, from a file already on disk.

## 7. Epistemic tagging, enforced

A `Tag` enum (`OBSERVED`, `MODEL_IMPLIED`, `INTERPRETATION`) is a required field
on every row emitted by the table builders in `episode/`, set at construction,
and rendered into every figure caption. An interpretation cannot reach a
deliverable without carrying its label. This is a data structure, not a docstring
convention, because the epistemic rule is the thing most likely to erode under
deadline.

`MODEL_IMPLIED_UNVALIDATED` is available but unused in this spec — ACM stays
inside its validated 1–10y range (§9).

## 8. Pre-specified windows

Fixed here, before any result is read. Baseline **27 Feb 2026**, the last
pre-shock close.

| # | Window | Horizon | Purpose |
|---|---|---|---|
| W1 | 27 Feb → 2 Mar / 3 Mar | 1d, 3d | onset — **confounded with the Spring Statement; reported, never load-bearing** |
| W2 | 27 Feb → 20 Mar | ~3wk | escalation peak |
| W3 | 18 → 19 Mar | 1d | MPC hawkish hold — clean policy event |
| W4 | 20 Mar → 15 May | ~8wk | the long-end leg |
| W5 | 8 Apr ±3d | 1d, 3d | ceasefire — does term premium fall on de-escalation? |
| W6 | 17 Jun ±3d | 1d, 3d | US–Iran MOU |
| W7 | 27 Feb → 19 Aug | cumulative | the headline episode |
| W8 | 7 Apr → 19 Aug | ~19wk | **energy unwind** — Brent −31% from its peak. Did the expectations component follow oil down, and did term premium? |

**Placebo windows:** matched-length windows drawn from the 12 months before the
shock, giving each reported move an empirical distribution. Every headline number
is scored against that distribution, not against zero.

**Baseline sensitivity:** W7 is recomputed from 26 Feb, 27 Feb and 4 Mar. The 4
Mar variant excludes the Spring Statement entirely. If the conclusion is not
robust across all three, it does not ship.

Windows are a versioned constant in `chronology.py` with a comment recording that
they were fixed on 2026-08-20 before results were read.

## 9. The long end — model-free by design

ACM stops at its validated 10y (the estimator's grid is 1–120 months, and the NY
Fed publishes no benchmark beyond 10y, so anything longer would be unvalidatable).
The 30y is handled with an identity that needs no model:

> 30y nominal +74bp = RPI breakeven +8bp + real yield +66bp

Both legs are BoE published curves (`glcinflationddata`, `glcrealddata`). The
finding — that the ultra-long selloff is a real-rate event with inflation
compensation anchored — is therefore OBSERVED, and cannot be attacked on
estimator grounds. This was an explicit design decision to trade model reach for
defensibility.

## 10. The five ways a macro PM kills this pitch

1. **"Your daily decomposition is mechanical."** ACM is estimated monthly and
   evaluated daily by projecting onto fixed PCA loadings; a parallel level shock
   loads on the level factor and lands in expected rates by construction, so
   "expectations dominate" could be an artifact.
   *Defence:* LDI and COVID show ACM does produce TP-dominated daily moves, so it
   is not structurally incapable of finding term premium. The +93bp SONIA OIS
   repricing at 2y corroborates the expectations call with no model at all. And
   §3.3's LDI-first-week wrinkle is reported, not hidden.
2. **"Term premium is a residual with fat standard errors."** 33bp RMSE against
   NY Fed at 10y; a +14bp TP change sits inside the noise.
   *Defence:* report changes not levels; carry the published US series as an
   independent second estimator; never let a TP number bear weight the observed
   evidence does not independently support.
3. **"27 Feb is cherry-picked and 3 March contaminates it."**
   *Defence:* §8 — pre-specified windows, baseline sensitivity including a
   post-Spring-Statement start, placebo distribution, W1 quarantined.
4. **"+9bp UK-minus-US is noise, and you are comparing three different curve
   fitters."** Anderson–Sleath vs GSW vs Svensson.
   *Defence:* score the differential against its own trailing distribution; show
   all three sources; use each source's native convention rather than forcing a
   common refit, and say so.
5. **"Structural supply makes the long end permanently cheaper."** QT review 17
   Sep, Autumn Budget, fading pension de-risking demand.
   *Defence:* this is H3 and it is the strongest counter, which is why §11 Step 6
   computes net DV01 to private investors rather than debt/GDP, and why the
   expression is expected to be a spread rather than outright duration.

## 11. Minimum viable empirical exercise

Deliberately small. Each item earns its place by changing the investment
conclusion.

1. Chronology and windows as versioned constants.
2. ACM event study at 2y/5y/10y across W1–W7 plus placebos (frozen estimator).
3. SONIA OIS and meeting-dated Bank Rate corroboration at the same windows —
   does observable front-end pricing back the ACM expected-rate move?
4. Model-free 30y decomposition: nominal = breakeven + real.
5. Cross-market UK/US/DE matched-maturity changes, UK-minus differentials, plus
   the NY Fed published US decomposition as a second estimator.
6. Net DV01 supplied to private investors: DMO gross issuance × approximate
   duration, less redemptions, plus APF sales and maturities.
7. Historical-episode benchmark table (§3.3) as a gate.
8. Trade expression table, research note, 90-second pitch.

Explicitly out of scope: positioning data (no reliable free UK source — its
absence is stated in the note rather than proxied), inflation swaps (BoE RPI
curve covers the need), any re-estimation or extension of ACM, any threshold or
trading rule fitted on the historical episodes.

## 12. Hypotheses to attack adversarially

- **H1 policy repricing** — the shock genuinely raised persistent UK inflation
  risk and the equilibrium BoE path. *Do not fade.*
- **H2 temporary term-premium shock** — uncertainty, positioning, risk aversion.
  *Value in receiving duration once the catalyst stabilises.*
- **H3 structural term-premium repricing** — persistent fiscal, duration-supply
  and structural-demand change. *Apparent cheapness is not mean reversion.*
- **H4 global duration shock** — the UK move is largely global. *A cross-market
  trade is cleaner than outright gilts.*

The strongest case for each is written before the conclusion is reached. Current
evidence tilts toward H1+H4, but §3.1 shows the 5y breakeven at +43bp against the
30y at +8bp, which is an energy-passthrough shape rather than a persistence
shape — so H1 must be attacked as hard as the others.

## 13. Trade construction

Universe open: cross-market spreads, outright gilts and gilt futures, SONIA swaps
and curve trades, and inflation/breakeven expressions. "No trade" is a
permissible conclusion.

For the preferred expression the trade table reports: thesis, instrument, entry
level, carry and roll, DV01, catalyst, **falsification condition**, and tails
(sharp further energy rise, UK recession, higher inflation persistence, fiscal
credibility deterioration, global risk-asset collapse).

A trade without a falsification condition is incomplete and will not ship.

## 14. Deliverables

- **F1** Δy = ΔE[r] + ΔTP stacked by tenor, cumulative window. Readable by a PM
  in five seconds.
- **F2** UK/US/DE matched-maturity changes plus UK-minus differentials against
  their own historical distribution.
- **F3** evidence panel: OIS front-end repricing vs ACM E[r]; breakeven curve
  shift (5y vs 30y); Brent and GBP.
- **T1** duration supply and QT · **T2** historical-episode benchmark · **T3**
  trade expression.
- `docs/notes/2026-gilt-selloff.md` — research note and 90-second pitch.

House style from `figures/style.py`; narrative captions baked into each image via
the `captioning-figures` skill. No dashboard.

## 15. Data sources — all free, all verified reachable 2026-08-20

| Source | Content | Endpoint |
|---|---|---|
| BoE yield curves | nominal, real, inflation, OIS daily histories + current month | `bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/{glcnominalddata,glcrealddata,glcinflationddata,oisddata,latest-yield-curve-data}.zip` |
| Fed Board | GSW zero curve | `federalreserve.gov/data/yield-curve-tables/feds200628.csv` |
| NY Fed | published ACM, monthly **and daily** sheets | `newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls` |
| Bundesbank | daily Svensson Bund zeros | `api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R{nn}XX.R.A.A._Z._Z.A?format=csv` |
| FRED | Brent, GBPUSD, DGS10/30, T10YIE | `fred.stlouisfed.org/graph/fredgraph.csv?id=<series>` |
| DMO | gilt operations, gilts in issue, gross/net issuance | `dmo.gov.uk/data/gilt-market/` |

Coverage confirmed to 19–20 Aug 2026 on every gilt, OIS, breakeven and US series.

**No LSEG/Refinitiv dependency.** European gas (TTF) is the only series with no
free daily source; Brent carries the energy signal and the note states the TTF
gap explicitly. Keeping the project terminal-free preserves reproducibility and
keeps secrets out of the repo.

Note: `urllib` timed out against the BoE CDN in this environment while `curl`
succeeded on the same URLs. The ingest layer needs a documented fallback or an
explicit long timeout; this is an environment quirk to handle, not a BoE outage.

## 16. Testing

- Unit tests on synthetic data for the window builder, the event-study algebra
  (Δy must equal ΔE[r] + ΔTP to floating-point tolerance), the placebo sampler,
  and the DV01 supply aggregation.
- Parser tests for each new ingest adaptor against a small committed fixture.
- One real-data test per source, network-gated and auto-skipping offline, matching
  the existing suite's convention.
- A regression test asserting the §3.1/§3.2 headline numbers, so a silent data or
  wiring change is caught.
- The §3.3 historical-episode gate: dysfunction episodes must be TP-dominated,
  policy episodes expectations-dominated. Assertions only — no thresholds tuned,
  no trading rule fitted.

## 17. Success criteria

1. `scripts/run_episode.py` reproduces §3.1 and §3.2 from raw downloads.
2. Every deliverable row and caption carries an epistemic tag.
3. The conclusion survives all three baselines in §8.
4. The trade table carries a falsification condition.
5. The note states, in one sentence a PM can repeat, how much of the UK move was
   global and how much was UK-specific.

## 18. Guiding constraint

Maximum investment insight per unit of additional modelling complexity. Every
addition above buys an answer to a question a PM will actually ask. ACM is used
for diagnosis, never prediction, and no forecasting skill is claimed from it.
