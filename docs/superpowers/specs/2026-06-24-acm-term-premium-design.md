# ACM Term-Premium Module — Design Spec

**Date:** 2026-06-24
**Status:** Approved (brainstorming), pending implementation-plan
**Extends:** existing `giltcurve` package (Objectives 1–4 done: SONIA OIS ingest,
bootstrap, forwards, implied Bank Rate path).

---

## 1. Objective

Implement the term-premium decomposition (roadmap Objectives 5–6):

> nominal yield = expected average short rate + term premium

via a regression-based **Adrian–Crump–Moench (ACM)** affine model. The estimator
is **currency-agnostic**: it consumes a zero-coupon yield panel (date × maturity)
plus a currency *label*, and the math never branches on the label. Output is a
clean, reusable decomposed panel keyed by `(date, currency, maturity)` that
serves two masters: the centerpiece of the GBP project, and the front end of a
downstream cross-currency basis project.

## 2. Scope (this spec)

**In:** US correctness anchor (GSW + NY Fed ACM) and GBP core — Steps A–E of the
brief: nominal gilt ingest, `premium/pca.py`, `premium/acm.py`, validation
script, downstream hooks, tests.

**Out (follow-up spec):** EUR (ECB AAA) and JPY (JGB) loaders. Deferred per the
brief's "ship validated USD+GBP rather than a broken 4-currency" guidance and the
"build the US anchor before trusting GBP" sequencing.

## 3. Constraints inherited from the repo

- From-scratch numpy/scipy on the critical path; `rateslib`/`QuantLib` only as
  optional cross-validation (`[validate]` extra). No black-box pricer in the ACM.
- Continuously-compounded decimal rates; `D(t)=exp(-R t)` (pinned to BoE forwards
  at 0.16bp). Reuse `conventions.py`, `DiscountCurve`, and the `ingest/boe.py`
  parse pattern.
- TDD: tests first; focused unit tests on synthetic data; one real-data
  integration check per area that **auto-skips offline** (mirrors existing
  `test_boe_ingest` network handling).
- Runner script performs **halt-on-failure** validation and prints a validation
  table, mirroring `scripts/run_policy_path.py`.
- Tidy `pandas` DataFrames as the public output of reporting/decomposition layers.

## 4. Key design decisions (resolved in brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Scope | US + GBP core; EUR/JPY deferred | Validate estimator before trusting GBP; one bounded spec. |
| Estimation frequency | **Monthly** (end-of-month), holding period `h = 1/12` | Canonical ACM; matches NY Fed published monthly series; avoids overlapping-return autocorrelation. |
| Daily output | Estimate parameters monthly, then evaluate the affine map on the daily curve | `term_premium_t = fitted − risk_neutral` is `A_n + B_n·X_t`; once parameters are fixed, project daily yields onto monthly PCA loadings to get daily `X_t`. |
| Maturity range (validated core) | **1–10y** | Range where the NY Fed ACM anchor exists. Panel still exposes the full estimated grid. |
| Model working grid | Resampled **monthly-maturity** grid `n = 1..120 months` | Textbook ACM; `n−h` is the adjacent node; clean risk-free at `n=1m`. |

## 5. Architecture

```
src/giltcurve/
├── ingest/
│   ├── boe_gilt.py     # nominal gilt zero-coupon curve (reuse boe.py pattern)
│   └── fed.py          # GSW zero curve + NY Fed ACM term premia (validation CSVs)
├── premium/
│   ├── __init__.py
│   ├── pca.py          # yield_pca(panel, k=5)
│   ├── acm.py          # fit_acm(...) + decompose(...) ; three-step OLS, from scratch
│   └── panel.py        # decomposed_panel(...) + cross_currency_differentials(...)
scripts/run_term_premium.py   # US anchor -> GBP decomp -> shape tests; halt-on-failure
tests/
├── test_boe_gilt.py
├── test_pca.py
├── test_acm.py
└── test_panel.py
```

### 5.1 `ingest/boe_gilt.py`
Ingest the BoE Anderson–Sleath **nominal gilt** zero-coupon curve (daily, from
1979) from the same BoE yield-curves source, reusing `parse_ois_sheet`'s
mechanics (multi-sheet xlsx, `years:` header row, dates in column A, percent→
decimal). The nominal-gilt workbook differs from the OIS workbook in filename and
sheet set; confirm the actual workbook name, spot-sheet name, maturity grid and
date range against the live archive during implementation (do not hard-assume).
No values on non-trading days. Returns a panel DataFrame `index=date,
cols=maturity(yrs)` plus a `latest`/`DiscountCurve` helper analogous to
`boe.py`. The historical (multi-decade) archive — not just the current month —
is required for ACM estimation; locate the BoE "GLC nominal" history files.

### 5.2 `ingest/fed.py`
- **GSW zero curve:** Fed Board Gürkaynak–Sack–Wright daily zero-coupon yields
  (`feds200628`), parsed to the same `(date × maturity)` panel shape. Continuously
  compounded; align to project conventions.
- **NY Fed ACM term premia:** published `ACMTP01..ACMTP10` (and `ACMY`, `ACMRNY`)
  monthly series, parsed to a `(date × maturity)` panel for the correctness
  anchor.
Both are public CSV downloads; cache like `download_boe_zip`.

### 5.3 `premium/pca.py`
`yield_pca(panel, k=5) -> PCAResult` with:
- `mean` (per-maturity), `loadings` W (N×K), `factors` X (T×K), `explained_var`
  ratios. First three components are level/slope/curvature (report variance
  explained; tests assert ordering and that PC1 loadings are same-sign).
- A `project(yields) -> factors` method so daily yields map onto monthly-estimated
  loadings for daily output.
Implemented from scratch via `numpy.linalg.svd` / eigdecomposition of the
demeaned panel covariance. Tested against known PCA properties on the real gilt
panel and synthetic data.

### 5.4 `premium/acm.py` — the centerpiece
`fit_acm(panel, *, k=5, currency, freq="M") -> ACMResult`, holding `mu, Phi,
Sigma, beta, lambda0, lambda1, delta0, delta1, A, B, A_rn, B_rn, pca`. Pure numpy
three-step OLS (Section 6). `decompose(result, panel_or_curve) -> DataFrame`
keyed `(date, currency, maturity)` with `{observed, fitted, expected_rate,
term_premium}`, where `expected_rate = risk-neutral yield` and `term_premium =
fitted − risk_neutral`. Optional `rateslib`/QuantLib cross-check is **not** on the
critical path.

### 5.5 `premium/panel.py` — downstream hooks
- `decomposed_panel(...)` returning the full-grid tidy panel keyed
  `(date, currency, maturity)`.
- `cross_currency_differentials(panels, tenor, base="USD") -> DataFrame`:
  per-currency, per-date `{exp_rate_diff, term_premium_diff}` vs USD.
- **HARD CONSTRAINT (explicit comment in the file):** this module does NOT regress
  any currency's basis on its own term premium over time — circular and out of
  scope. It only produces decomposed rate components; cross-sectional basis
  modeling happens downstream and across currencies.

## 6. ACM math (from scratch — to be carried verbatim into code docstrings)

Per-period `h = 1/12` (monthly). Yields `y` continuously compounded, decimal.
Model working grid: monthly maturities `n = 1,2,…,120` months, obtained by
resampling each date's curve via `DiscountCurve` interpolation.

1. **Pricing factors.** PCA of the demeaned monthly yield panel → factors
   `X_t ∈ R^K` (K=5), loadings `W`, mean `ȳ`.

2. **VAR(1).** `X_{t+1} = μ + Φ X_t + v_{t+1}`, estimated by OLS equation-by-
   equation; innovations `v`; `Σ = cov(v)`.

3. **Excess holding returns.** Log price `p^{(n)}_t = −n · y^{(n)}_t`. One-period
   excess return of the n-maturity bond:
   `rx^{(n)}_{t+1} = p^{(n−h)}_{t+1} − p^{(n)}_t − r^{(h)}_t`,
   with one-period risk-free `r^{(h)}_t = −p^{(h)}_t = h · y^{(1m)}_t`.

4. **Three-step OLS** (Adrian–Crump–Moench 2013):
   - Regress the N×T stack `rx_{t+1}` on a constant, lagged factors `X_t`, and
     contemporaneous innovations `v_{t+1}`:
     `rx_{t+1} = a + c·X_t + β·v_{t+1} + e_{t+1}` → `a` (N×1), `c` (N×K),
     `β` (N×K), residual var `σ² = mean diag(cov(e))`.
   - Cross-sectional recovery of prices of risk:
     `λ₁ = (β'β)⁻¹ β' C` where `C` stacks `c`;
     `λ₀ = (β'β)⁻¹ β' a*`, with convexity-adjusted intercept
     `a* = a + ½ ( diag(β Σ β') + σ² )`.
   - Short-rate equation `r_t = δ₀ + δ₁' X_t` by OLS of the 1-month yield on `X_t`.

5. **Affine recursions** (`A_0=0, B_0=0`):
   `A_{n+1} = A_n + B_n'(μ − λ₀) + ½(B_n' Σ B_n + σ²) − δ₀`
   `B_{n+1}' = B_n'(Φ − λ₁) − δ₁'`
   Fitted yield `y^{(n)} = −(A_n + B_n' X_t)/n`.
   **Risk-neutral**: identical recursions with `λ₀=λ₁=0` → `A_n^{RN}, B_n^{RN}`.
   **Expected-rate component** = risk-neutral yield;
   **term premium** = fitted − risk-neutral.

## 7. Validation (credibility — halt on failure)

1. **US external anchor (correctness proof).** Run the *same* estimator on GSW;
   compare model 1–10y term premia to NY Fed `ACMTP*`. **Halt** if correlation
   `< ~0.95` (per tenor) or levels diverge beyond a stated tolerance. This proves
   the estimator before it is trusted on GBP, which has no published benchmark.
2. **GBP internal anchor.** Compare the ACM expected-rate path against the
   existing SONIA implied Bank Rate path (`policy/meeting_dated.py`). Report the
   gap as a model-robustness diagnostic. **Comparison is on shape/changes, not
   levels**, because ACM is gilt-based and the path is OIS-based (a gilt/swap
   asset-swap spread separates them); this is flagged in the diagnostic output.
3. **Shape tests (halt on failure).** Term premium ≈ 0 at the short end and rising
   with maturity (on average); 10y term premium rises in a risk-off episode (e.g.
   late-2008) and compresses during QE.

Real-data validations auto-skip offline, mirroring the existing integration check.

## 8. Output artefacts

- `data/processed/term_premium_panel.csv` — tidy `(date, currency, maturity) ->
  {observed, fitted, expected_rate, term_premium}`.
- `reports/figures/` — term premium by tenor over time; 10y decomposition stack;
  US ACM overlay (ours vs NY Fed).
- A README validation table (in the style of the existing one) and a short methods
  note: ACM spec, US-as-correctness-anchor logic, expected-rate-vs-SONIA-path
  robustness result. Roadmap table updated marking Objectives 5–6 done.

## 9. Flagged judgment calls (documented, not silently chosen)

1. **1-month risk-free.** GSW starts at 1y, the gilt curve at ~6m, so the 1-month
   node comes from left-extrapolation (flat zero below the first pillar, per
   `DiscountCurve`). Affects excess-return *levels* slightly; ACM is robust.
   Default: flat-zero extrapolation, documented in `acm.py`.
2. **GBP expected-rate vs SONIA path** compares a gilt-based decomposition to an
   OIS-based path; gilt/swap spread ⇒ compare shape/changes, not levels.
3. **EUR/JPY** deferred to a follow-up spec.

## 10. Out of scope / non-goals

- Cross-sectional cross-currency basis modeling (downstream project).
- State-space / Kalman ML estimation (brief specifies regression-based ACM).
- Real (index-linked) curve and breakeven decomposition (Objective 7, later).
```
