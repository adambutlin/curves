# UK Gilt / SONIA OIS Yield-Curve Construction, Forward Extraction & Term-Premium Decomposition

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

## What is implemented (this slice)

A complete, tested, real-data pipeline for **Objectives 1–4**:

1. **Curve construction** — ingest the Bank of England's published SONIA OIS curve.
2. **Bootstrapping** — strip discount factors from par OIS quotes, from scratch.
3. **Forward extraction** — zero rates, instantaneous and period forwards.
4. **Implied Bank Rate path** — forwards sliced at MPC meeting dates (≈ WIRP).

The numerical core is built from scratch in **numpy/scipy** — no black-box
pricing library on the critical path — so the mathematics is fully inspectable.
`rateslib` / `QuantLib` are wired in only as optional cross-validation
(`pip install -e ".[validate]"`).

### Headline result (BoE curve, as of 19 Jun 2026)

![implied policy path](reports/figures/implied_policy_path.png)

The front end prices a gradual rise in forward SONIA of **~+45bp to end-2027**.
Note this is the *raw* forward path, which conflates expected policy with term
premium — disentangling the two is the next phase (ACM), and is exactly why the
term-premium decomposition matters.

### Validation (on real BoE data, reported by the runner)

| Check | Result | What it proves |
|---|---|---|
| Bootstrap round-trip (par → DF → bootstrap) | **max |ΔDF| = 1.1e-16** | the bootstrap is the exact algebraic inverse of par pricing |
| Our forwards vs BoE's *published* instantaneous forwards | **RMSE = 0.16 bp** | the compounding convention matches the BoE's own |

The continuous-compounding convention (`D(t)=exp(−R(t)·t)`) was **pinned
empirically**, not assumed: it reproduces BoE's published forward curve to 0.3bp
vs 8.5bp for annual compounding.

---

## Architecture

```
curves/
├── data/
│   ├── raw/            # BoE workbooks (re-fetchable; git-ignored)
│   └── processed/      # implied_policy_path.csv
├── src/giltcurve/
│   ├── conventions.py          # day-count, spot<->DF (continuous)
│   ├── ingest/boe.py           # download + parse BoE SONIA OIS curve
│   ├── curves/
│   │   ├── discount.py         # DiscountCurve (log-linear in log DF)
│   │   ├── ois_bootstrap.py    # par OIS -> discount factors (Step 2)
│   │   └── forwards.py         # zero/forward reporting tables (Step 3)
│   ├── policy/
│   │   ├── mpc.py              # MPC meeting-date calendar
│   │   └── meeting_dated.py    # implied Bank Rate path (Step 4)
│   └── viz/plots.py            # desk-style charts
├── scripts/run_policy_path.py  # end-to-end pipeline + validations
├── tests/                      # 32 tests (TDD); 1 real-data integration check
├── reports/figures/            # generated charts
└── notebooks/                  # (narrative analysis — roadmap)
```

## Quickstart

```bash
python3 -m pip install -e ".[dev]"   # or: pip install numpy scipy pandas matplotlib openpyxl pytest
python3 -m pytest                    # 32 passing (real-data check auto-skips if offline)
python3 scripts/run_policy_path.py   # downloads BoE curve, prints path + validations, saves charts
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
| Yield-curve PCA | `premium/pca.py` | level/slope/curvature; foundation for ACM |
| **Term premium (ACM)** | `premium/acm.py` | the centerpiece: split yields into expected-rate + term premium |
| Breakeven decomposition | `inflation/breakevens.py` | nominal vs index-linked gilts; **RPI wedge** + 2030 reform |
| Cross-checks & divergence | `notebooks/` | implied path vs Consensus; flag pricing inconsistent with fundamentals |

## Caveats

- **MPC dates** for 2026–2027 in `policy/mpc.py` are projected from the BoE's
  ~6-weekly cadence and should be reconciled against the official calendar.
- **SONIA → Bank Rate basis** (`bank_rate_minus_sonia_bp`) is a small, explicit
  parameter; it cancels from *changes* in the path, so the cumulative-bp figure
  is the robust headline.
