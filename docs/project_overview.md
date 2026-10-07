# Sovereign Yield Curves: Structural Origins, Propagation and Term Premia

*This overview was the repository's front page until October 2026. The front page now presents the research note on the 2026 Treasury selloff ([../README.md](../README.md)); this file describes the wider programme and the curve-construction and term-premium toolkit it rests on.*

## Current research: does the origin of a yield move predict what follows?

A rise in sovereign yields is not itself a shock: the same 15bp move can come from
monetary repricing, growth news, inflation news or a change in risk compensation.
The current programme asks whether knowing **why** yields moved today says anything
about **how** the curve evolves over the next 1-20 trading days. A daily
sign-restricted Bayesian VAR (after Cieslak and Pang, 2021) extracts growth,
monetary, common-premium and hedging-premium shocks from Treasury yields and
equities; propagation tests then condition on the observed move and compare the
structural state with momentum, curve-state and reduced-form benchmarks, in sample
and in real time. 2026 is held out and sealed in the data layer.

**Result so far (US Treasuries, 1983-2025; three pre-registered designs).** The
published Cieslak-Pang decomposition is reproduced almost exactly. In sign, origin
matters: moves driven by news about the expected course of policy rates continue, while
risk-premium shocks do not, most clearly when bonds and stocks fall together. As a
forecasting claim about the 10-year yield the answer is no: the effect explains at most
a fraction of a percent of subsequent variance, a random split of the same news does
about as well, and nothing beats a no-change forecast in real time, whether the shocks
are identified once, within stock-bond regimes, or with large news treated separately.
The continuation that exists sits in ordinary-sized news; large, salient policy news is
priced at once.

**Cross-Atlantic model and 2026.** Brandt et al.'s (2021) euro-area/US model is
replicated closely once euro-area prices are recorded at the New York close (LSEG data):
the US share of euro-area rate variance is 35-40% against their 40%, and equity and FX
spillovers match. On free data, whose European prices close five and a half hours early,
the same model finds spurious next-day "propagation"; synchronised, its answer matches
the US model's. Run frozen through 2026, the models put US news at the centre: the
euro-area 10-year rate's rise was imported almost entirely, and the 2-year Treasury's
rise was a repricing of US policy-rate expectations.

**The 2026 gilt selloff.** A UK-US version of the model, with an added UK risk-premium
shock (gilts selling off while sterling falls, the signature of a fiscal-credibility
scare, which it correctly finds in the 2022 mini-budget), attributes 84-91bp of the
10-year gilt's 95bp rise in 2026 to US news and global risk sentiment. The domestic part
was Bank of England repricing that lifted sterling too; the risk premium contributed
-7bp. The gilt-vigilante reading of 2026 is not supported.

- Overview and reading order: [docs/research/structural-propagation/README.md](research/structural-propagation/README.md)
- MVP results: [03-mvp-results.md](research/structural-propagation/03-mvp-results.md); regime-dependent identification: [05-phase2-results.md](research/structural-propagation/05-phase2-results.md); size of news: [07-phase3-results.md](research/structural-propagation/07-phase3-results.md); cross-Atlantic model: [09-brandt-results.md](research/structural-propagation/09-brandt-results.md), synchronised: [12-brandt-synchronised-results.md](research/structural-propagation/12-brandt-synchronised-results.md); UK: [14-ukus-results.md](research/structural-propagation/14-ukus-results.md); 2026: [10-2026-application.md](research/structural-propagation/10-2026-application.md)
- Figures and tables: [reports/structural_propagation/](../reports/structural_propagation/)

```bash
python scripts/run_structural_propagation.py      # MVP: estimation, tests, real-time evaluation (~2 min)
python scripts/run_phase2_regimes.py              # regime-specific identification (~1.5 min)
python scripts/run_phase3_size.py                 # size-dependent propagation (~2 min)
python scripts/plot_structural_propagation.py     # figures 1-6
python scripts/run_brandt.py                      # cross-Atlantic model (Brandt et al.)
python scripts/run_2026_application.py --brandt-sha <frozen model hash>   # both models on 2026
python scripts/run_brandt.py --sync ois          # synchronised version (LSEG Workspace + LSEG_APP_KEY)
python scripts/plot_brandt_2026.py                # figures 7-14
python scripts/run_ukus.py                        # UK-US models (LSEG)
python scripts/plot_ukus.py                       # figures 15-17
```

---

## Curve construction and term-premium toolkit

The infrastructure below supplies the yield curves and the term-premium model the
research uses.

A research-grade fixed-income project that reads **what the market prices about
future monetary policy, inflation and risk premia** out of UK rates. The spine
of the project is one decomposition:

> **nominal yield = expected average short rate + term premium**

and its inflation analogue (`breakeven = expected inflation + inflation risk
premium − liquidity premium`). Everything here — curve construction,
bootstrapping, forwards, the policy path, and the planned term-premium model —
exists to populate that decomposition and then ask *where the market's implied
story disagrees with macro fundamentals.*

This is **SONIA-native** (post-LIBOR): the GBP risk-free discount curve is the
SONIA OIS curve, and Bank Rate expectations are read from **meeting-dated OIS**.

---

## What is implemented

A complete, tested, real-data pipeline for **Objectives 1–6**:

1. **Curve construction** — ingest the Bank of England's published SONIA OIS curve.
2. **Bootstrapping** — strip discount factors from par OIS quotes, from scratch.
3. **Forward extraction** — zero rates, instantaneous and period forwards.
4. **Implied Bank Rate path** — forwards sliced at MPC meeting dates (≈ WIRP).
5. **Yield-curve PCA** — level/slope/curvature pricing factors (`premium/pca.py`).
6. **Term-premium decomposition (ACM)** — split the nominal gilt yield into an
   expected-average-short-rate component and a term premium, via a from-scratch
   Adrian–Crump–Moench affine model, *proven against the NY Fed's published series*
   (`premium/acm.py`; see [Term-premium decomposition](#term-premium-decomposition-acm)).

The numerical core is built from scratch in **numpy/scipy** — no black-box
pricing library on the critical path — so the mathematics is fully inspectable.
`rateslib` / `QuantLib` are wired in only as optional cross-validation
(`pip install -e ".[validate]"`).

### Validation (on real BoE data, reported by the runner)

| Check | Result | What it proves |
|---|---|---|
| Bootstrap round-trip (par → DF → bootstrap) | **max |ΔDF| = 1.1e-16** | the bootstrap is the exact algebraic inverse of par pricing |
| Our forwards vs BoE's *published* instantaneous forwards | **RMSE = 0.16 bp** | the compounding convention matches the BoE's own |

The continuous-compounding convention (`D(t)=exp(−R(t)·t)`) was **pinned
empirically**, not assumed: it reproduces BoE's published forward curve to 0.3bp
vs 8.5bp for annual compounding.

---

## Term-premium decomposition (ACM)

The centerpiece: split the **nominal government-bond yield** into an
expected-average-short-rate component and a **term premium**, via a from-scratch,
regression-based **Adrian–Crump–Moench (ACM)** affine model. The estimator is
**currency-agnostic** — it consumes a generic zero-coupon yield panel plus a
currency *label* and never branches on it — so the same code runs on US Treasuries
and UK gilts and emits a tidy decomposed panel keyed by `(date, currency,
maturity)`, ready for a downstream cross-currency-basis project.

As of Jun 2026 the **10y gilt (≈4.87%)** splits into a **~3.74% expected average
short rate** and a **~113bp term premium**.

### Validation — US as the correctness anchor

The estimator is proven on **US Treasuries before it is trusted on gilts** (which
have no published benchmark): the *same* code runs on the Fed Board's GSW zero
curve and must reproduce the **New York Fed's published ACM term premia**
(1961–2026, 780 monthly observations). The runner **halts** if it doesn't.

| Check | Result | What it proves |
|---|---|---|
| GSW → our ACM vs NY Fed ACM, **10y** | **corr 1.00**, RMSE 33bp | the from-scratch estimator reproduces a published benchmark |
| GSW → our ACM vs NY Fed ACM, **5y** | **corr 0.99** | the match holds across the belly |
| Term-premium **shape** (US & GBP) | ≈0 at the short end, **rising to 10y** | correct affine behaviour (halt-on-failure) |
| GBP ACM 2y expected-rate vs **SONIA implied path** | gap **−11bp** | model-robustness; the gap is the expected gilt/OIS basis |

The gate is on the data-supported **5y/10y** tenors. The **1y/2y** correlations
(0.82/0.93) are reported but *not* gated: the GSW curve has no reliable sub-1y
data, so the 1-month risk-free is extrapolated, which biases the front-end premium
low — a documented data limitation, not an estimator error.

**Methods note.** Five PCA pricing factors (the first three are the classic
level/slope/curvature, explaining **>99.9%** of yield variance — 99.99% for gilts,
99.997% for GSW) feed a **VAR(1)** for their dynamics, then a **three-step OLS**
prices one-period excess holding returns to recover the prices of risk (λ₀, λ₁),
and **affine recursions** build `A_n, B_n`. The **fitted** yield uses the estimated
prices of risk; the **risk-neutral** yield sets them to zero; **expected-rate =
risk-neutral yield** and **term premium = fitted − risk-neutral**. Parameters are
estimated monthly and can be evaluated on the daily curve. The numerics are pure
numpy/scipy on the critical path. Run it:

```bash
python3 scripts/run_term_premium.py   # US anchor -> GBP decomposition; halts on failure
```

---

## Architecture

```
curves/
├── data/
│   ├── raw/            # BoE / Fed / NY Fed downloads (re-fetchable; git-ignored)
│   └── processed/      # runner outputs (regenerable; git-ignored)
├── src/giltcurve/
│   ├── conventions.py          # day-count, spot<->DF (continuous)
│   ├── ingest/
│   │   ├── boe.py              # download + parse BoE SONIA OIS curve
│   │   ├── boe_gilt.py         # BoE nominal gilt zero curve (ACM input, 1979-)
│   │   └── fed.py              # GSW zero curve + NY Fed ACM (US validation anchor)
│   ├── curves/
│   │   ├── discount.py         # DiscountCurve (log-linear in log DF)
│   │   ├── ois_bootstrap.py    # par OIS -> discount factors (Step 2)
│   │   └── forwards.py         # zero/forward reporting tables (Step 3)
│   ├── policy/
│   │   ├── mpc.py              # MPC meeting-date calendar
│   │   └── meeting_dated.py    # implied Bank Rate path (Step 4)
│   ├── premium/
│   │   ├── pca.py              # PCA pricing factors (level/slope/curvature)
│   │   ├── acm.py              # ACM term-premium decomposition (from scratch)
│   │   └── panel.py            # decomposed panel + cross-currency differentials
│   ├── propagation/            # structural-origins study: data (2026 sealed), BVAR,
│   │                           #   sign restrictions, propagation tests, real-time evaluation
│   └── viz/plots.py            # desk-style charts
├── scripts/
│   ├── run_policy_path.py      # SONIA OIS pipeline + validations
│   ├── run_term_premium.py     # ACM: US anchor -> GBP decomposition (halt-on-fail)
│   └── *structural_propagation.py, run_phase2_regimes.py, run_phase3_size.py
├── docs/research/structural-propagation/   # design, pre-registrations, results
├── reports/structural_propagation/         # figures, tables, frozen end-2025 model
├── reports/figures/            # toolkit charts (generated; git-ignored)
└── tests/                      # 117 tests; real-data checks auto-skip offline
```

## Quickstart

```bash
python3 -m pip install -e ".[dev]"   # or: pip install numpy scipy pandas matplotlib openpyxl xlrd pytest
python3 -m pytest                    # 117 passing (network-gated ingest checks auto-skip offline)
python3 scripts/run_policy_path.py   # downloads BoE curve, prints path + validations, saves charts
python3 scripts/run_term_premium.py  # US anchor -> GBP ACM term-premium decomposition
```

## Data

- **Source:** Bank of England published UK yield curves — the same curve the MPC
  and UK desks watch, with published methodology (Anderson–Sleath VRP spline).
  Free and fully reproducible; no terminal required.
  `https://www.bankofengland.co.uk/statistics/yield-curves`
- **Desk path:** a `bloomberg.py` adaptor returning the same
  `(asof, maturities, rates)` tuple — or raw par-swap quotes straight into
  `bootstrap_ois` — drops in unchanged.

## Roadmap (Objectives 5–8)

| Phase | Module | Note |
|---|---|---|
| Yield-curve PCA | `premium/pca.py` | **done** — level/slope/curvature; >99.9% of variance in first 3 PCs |
| **Term premium (ACM)** | `premium/acm.py` | **done** — currency-agnostic ACM; reproduces NY Fed ACM (10y corr 1.00) |
| Breakeven decomposition | `inflation/breakevens.py` | nominal vs index-linked gilts; **RPI wedge** + 2030 reform |
| Cross-checks & divergence | (not started) | implied path vs Consensus; flag pricing inconsistent with fundamentals |

## Caveats

- **MPC dates** for 2026–2027 in `policy/mpc.py` are projected from the BoE's
  ~6-weekly cadence and should be reconciled against the official calendar.
- **SONIA → Bank Rate basis** (`bank_rate_minus_sonia_bp`) is a small, explicit
  parameter; it cancels from *changes* in the path, so the cumulative-bp figure
  is the robust headline.
- **ACM 1-month risk-free** is extrapolated where the curve has no sub-1y data
  (GSW starts at 1y), which biases the *front-end* (1y/2y) term premium low; the
  decomposition is validated and reported on **5y–10y**, where it reproduces the
  NY Fed ACM almost exactly.
- **ACM expected-rate vs SONIA path** is a *gilt*-vs-*OIS* comparison, so read it
  on shape/changes, not levels — the gap is the gilt/swap (asset-swap) basis.
