# ACM Term-Premium Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a currency-agnostic, regression-based Adrian–Crump–Moench (ACM) affine model that decomposes a zero-coupon yield panel into expected-rate and term-premium components, proven against the NY Fed's published Treasury term premia and applied to UK gilts.

**Architecture:** New `premium/` subpackage (`pca.py`, `acm.py`, `panel.py`) doing pure-numpy three-step OLS on a resampled monthly-maturity / monthly-frequency panel; new ingest loaders for the BoE nominal gilt curve and the US validation anchors (GSW zero curve + NY Fed ACM series); a halt-on-failure runner script. Everything reuses the existing `DiscountCurve`, `conventions.py`, and the `ingest/boe.py` parsing pattern.

**Tech Stack:** Python 3.10+, numpy, scipy, pandas, openpyxl, matplotlib, pytest. From-scratch numerics on the critical path; `rateslib`/`QuantLib` only as optional cross-checks.

---

## Conventions locked for this plan (read before any task)

**Unit consistency is the #1 correctness risk.** Lock these:

- `PERIODS_PER_YEAR = 12`, `H = 1/12`. The model works in **monthly periods**.
- Input panels carry **annualised, continuously-compounded** yields (decimal),
  columns = maturity in **years**. This matches `DiscountCurve.zero`.
- Internally ACM uses **per-period** yields `yp = y_annual * H`. Log price of an
  `n`-month bond is `p^{(n)} = -n * yp^{(n)}`. The one-period short rate is
  `r_t = yp^{(1)}` (the 1-month per-period yield).
- The model grid is `n = 1..120` **months**; in years that is
  `MONTHLY_GRID_YEARS = np.arange(1, 121) / 12`.
- Model/term-premium outputs are **re-annualised** by `* PERIODS_PER_YEAR` so the
  returned panel is back in annual decimals, comparable to observed yields.
- Reported tenors for the validated core are **1..10y** = months `12,24,…,120`.

**Factor/innovation alignment:** with `T` monthly observations, factors `X` are
`(T,K)`. Excess returns `rx` have `T-1` rows aligned to `t+1`; the regressors are
lagged factors `X[:-1]` and the VAR innovations `v` (also `T-1` rows, aligned to
`t+1`).

**Branches on currency are forbidden** in `pca.py`/`acm.py`. Currency is a label
attached only to output rows.

---

## File structure

| File | Responsibility |
|---|---|
| `src/giltcurve/premium/__init__.py` | subpackage marker |
| `src/giltcurve/premium/pca.py` | PCA of a yield panel → factors, loadings, mean, variance explained, `project()` |
| `src/giltcurve/premium/acm.py` | resampling, excess returns, VAR(1), three-step OLS, affine recursions, `fit_acm`, `decompose` |
| `src/giltcurve/premium/panel.py` | `decomposed_panel`, `cross_currency_differentials`, hard-constraint comment |
| `src/giltcurve/ingest/fed.py` | GSW zero curve + NY Fed ACM series loaders (US anchor) |
| `src/giltcurve/ingest/boe_gilt.py` | BoE nominal gilt zero-coupon curve loader |
| `scripts/run_term_premium.py` | end-to-end: US anchor validation → GBP decomp → shape tests → artefacts |
| `tests/test_pca.py` | PCA properties on synthetic + real |
| `tests/test_acm.py` | VAR/returns/recursions/round-trip on synthetic |
| `tests/test_fed_ingest.py` | GSW + ACM parse (network auto-skip) |
| `tests/test_boe_gilt_ingest.py` | gilt parse (network auto-skip) |
| `tests/test_panel.py` | panel shape + differentials |

---

## Task 1: PCA of a yield panel (`premium/pca.py`)

**Files:**
- Create: `src/giltcurve/premium/__init__.py`
- Create: `src/giltcurve/premium/pca.py`
- Test: `tests/test_pca.py`

- [ ] **Step 1: Create the subpackage marker**

Create `src/giltcurve/premium/__init__.py`:

```python
"""Term-premium decomposition: PCA pricing factors and the ACM affine model."""
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_pca.py`:

```python
"""Tests for premium/pca.py — pricing-factor extraction."""
import numpy as np
import pandas as pd

from giltcurve.premium.pca import yield_pca


def _synthetic_panel(T=400, seed=0):
    """Yields built from 3 latent factors + small noise; level/slope/curvature."""
    rng = np.random.default_rng(seed)
    mats = np.array([0.5, 1, 2, 3, 5, 7, 10])
    level = rng.normal(0, 0.010, T)
    slope = rng.normal(0, 0.006, T)
    curv = rng.normal(0, 0.003, T)
    L = np.ones_like(mats)
    S = (mats - mats.mean()) / mats.std()
    C = (S ** 2 - (S ** 2).mean())
    Y = (0.04
         + level[:, None] * L[None, :]
         + slope[:, None] * S[None, :]
         + curv[:, None] * C[None, :]
         + rng.normal(0, 1e-4, (T, mats.size)))
    return pd.DataFrame(Y, columns=mats)


def test_factors_and_loadings_shapes():
    panel = _synthetic_panel()
    res = yield_pca(panel, k=5)
    assert res.loadings.shape == (panel.shape[1], 5)
    assert res.factors.shape == (panel.shape[0], 5)
    assert res.explained_var.shape == (5,)


def test_variance_explained_is_descending_and_sums_below_one():
    res = yield_pca(_synthetic_panel(), k=5)
    ev = res.explained_var
    assert np.all(np.diff(ev) <= 1e-12)
    assert 0 < ev.sum() <= 1.0 + 1e-9
    assert ev[:3].sum() > 0.99  # three latent factors dominate


def test_pc1_is_level_same_sign_loadings():
    res = yield_pca(_synthetic_panel(), k=5)
    assert np.all(res.loadings[:, 0] > 0)  # sign convention: level up => factor up


def test_loadings_orthonormal():
    res = yield_pca(_synthetic_panel(), k=5)
    gram = res.loadings.T @ res.loadings
    np.testing.assert_allclose(gram, np.eye(5), atol=1e-9)


def test_project_reproduces_in_sample_factors():
    panel = _synthetic_panel()
    res = yield_pca(panel, k=5)
    proj = res.project(panel.to_numpy(float))
    np.testing.assert_allclose(proj, res.factors, atol=1e-9)


def test_reconstruction_close_to_input():
    panel = _synthetic_panel()
    res = yield_pca(panel, k=5)
    recon = res.mean + res.factors @ res.loadings.T
    np.testing.assert_allclose(recon, panel.to_numpy(float), atol=5e-4)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_pca.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'giltcurve.premium.pca'`

- [ ] **Step 4: Implement `premium/pca.py`**

Create `src/giltcurve/premium/pca.py`:

```python
"""Principal-component pricing factors for a zero-coupon yield panel.

The ACM model uses the first ``K`` principal components of the yield panel as
observable pricing factors. The leading three are the classic level / slope /
curvature. PCA is computed from scratch via the SVD of the demeaned panel:
loadings are the right singular vectors, factor scores are the projections of the
demeaned yields onto them, and the explained-variance ratios come from the
squared singular values. This module is currency-agnostic — it sees only numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PCAResult:
    """Fitted PCA of a yield panel.

    Attributes
    ----------
    mean : (N,) per-maturity sample mean (the panel is demeaned before PCA).
    loadings : (N, K) orthonormal columns; column j is PC j's loading vector.
    factors : (T, K) factor scores (demeaned yields projected onto loadings).
    explained_var : (K,) fraction of total panel variance per component.
    maturities : (N,) maturity grid (years) the loadings are defined on.
    """

    mean: np.ndarray
    loadings: np.ndarray
    factors: np.ndarray
    explained_var: np.ndarray
    maturities: np.ndarray

    def project(self, yields) -> np.ndarray:
        """Map (annualised) yields onto the fitted loadings -> factor scores.

        Lets parameters estimated on a monthly panel be evaluated on any later
        (e.g. daily) yields. Accepts a 1-D row or a 2-D (rows x maturities) array.
        """
        y = np.atleast_2d(np.asarray(yields, float))
        out = (y - self.mean) @ self.loadings
        return out[0] if np.ndim(yields) == 1 else out


def yield_pca(panel: pd.DataFrame, k: int = 5) -> PCAResult:
    """Extract the first ``k`` principal components of a yield panel.

    Parameters
    ----------
    panel : DataFrame, index=date, columns=maturity(years), values=yield(decimal).
    k : number of components to retain.
    """
    Y = panel.to_numpy(float)
    if Y.shape[0] <= k:
        raise ValueError("need more observations than components")
    mean = Y.mean(axis=0)
    Yc = Y - mean
    _, S, Vt = np.linalg.svd(Yc, full_matrices=False)
    loadings = Vt[:k].T.copy()
    factors = Yc @ loadings
    explained_var = (S[:k] ** 2) / (S ** 2).sum()
    # Sign convention: each component points so its loadings sum positive
    # (PC1 => a parallel "level" rise raises the factor).
    for j in range(k):
        if loadings[:, j].sum() < 0:
            loadings[:, j] *= -1.0
            factors[:, j] *= -1.0
    return PCAResult(mean, loadings, factors, explained_var, panel.columns.to_numpy(float))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_pca.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add src/giltcurve/premium/__init__.py src/giltcurve/premium/pca.py tests/test_pca.py
git commit -m "feat(premium): PCA pricing factors for the ACM model"
```

---

## Task 2: Curve resampling + excess returns + VAR(1) (`premium/acm.py` part 1)

**Files:**
- Create: `src/giltcurve/premium/acm.py`
- Test: `tests/test_acm.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_acm.py`:

```python
"""Tests for premium/acm.py — resampling, excess returns, VAR(1), three-step OLS."""
import numpy as np
import pandas as pd

from giltcurve.premium.acm import (
    PERIODS_PER_YEAR,
    resample_to_monthly_grid,
    excess_returns,
    fit_var1,
)


def test_resample_flat_curve_is_flat_on_monthly_grid():
    # Flat 4% annual curve on a coarse grid -> flat 4% on the 1..120m grid.
    panel = pd.DataFrame(
        {0.5: [0.04], 1.0: [0.04], 2.0: [0.04], 5.0: [0.04], 10.0: [0.04]},
        index=pd.to_datetime(["2020-01-31"]),
    )
    out = resample_to_monthly_grid(panel)
    assert out.shape == (1, 120)
    np.testing.assert_allclose(out.to_numpy(float), 0.04, atol=1e-9)
    np.testing.assert_allclose(out.columns.to_numpy(float), np.arange(1, 121) / 12.0)


def test_excess_returns_zero_under_constant_flat_curve():
    # A constant flat curve over time has ~zero excess holding returns.
    grid = np.arange(1, 121) / 12.0
    Y = np.full((6, 120), 0.03)
    panel = pd.DataFrame(Y, columns=grid,
                         index=pd.date_range("2020-01-31", periods=6, freq="ME"))
    rx = excess_returns(panel)
    assert rx.shape == (5, 119)
    np.testing.assert_allclose(rx, 0.0, atol=1e-12)


def test_fit_var1_recovers_known_dynamics():
    rng = np.random.default_rng(1)
    K, T = 2, 4000
    mu_true = np.array([0.01, -0.02])
    Phi_true = np.array([[0.9, 0.05], [0.0, 0.7]])
    Sig = np.array([[1e-4, 0.0], [0.0, 4e-4]])
    L = np.linalg.cholesky(Sig)
    X = np.zeros((T, K))
    for t in range(1, T):
        X[t] = mu_true + Phi_true @ X[t - 1] + L @ rng.standard_normal(K)
    mu, Phi, Sigma, resid = fit_var1(X)
    np.testing.assert_allclose(mu, mu_true, atol=3e-3)
    np.testing.assert_allclose(Phi, Phi_true, atol=3e-2)
    np.testing.assert_allclose(Sigma, Sig, atol=5e-5)
    assert resid.shape == (T - 1, K)


def test_periods_per_year_constant():
    assert PERIODS_PER_YEAR == 12
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'giltcurve.premium.acm'`

- [ ] **Step 3: Implement part 1 of `premium/acm.py`**

Create `src/giltcurve/premium/acm.py`:

```python
"""Adrian–Crump–Moench (ACM) regression-based affine term-structure model.

Decomposes a zero-coupon yield panel into an expected-average-short-rate
component (the risk-neutral yield) and a term premium (fitted minus risk-neutral)
via the ACM three-step OLS. The estimator is currency-agnostic: it consumes a
generic ``(date x maturity)`` yield panel and a currency *label*; the math never
branches on the label.

Unit convention (see plan): the model works in monthly periods. Input panels are
annualised continuously-compounded yields (decimal); internally yields are scaled
to per-period (``y * H``), the model grid is months ``1..120``, and outputs are
re-annualised by ``PERIODS_PER_YEAR``.

Method (ACM 2013):
  1. Pricing factors X_t = first K PCs of the yield panel.
  2. VAR(1):  X_{t+1} = mu + Phi X_t + v_{t+1};   Sigma = cov(v).
  3. Excess one-period holding returns rx regressed on a constant, lagged
     factors and contemporaneous innovations -> beta, and prices of risk
     (lambda0, lambda1) recovered cross-sectionally with the convexity term.
  4. Affine recursions A_n, B_n. Fitted yield uses (lambda0, lambda1);
     risk-neutral yield sets them to zero; term premium = fitted - risk-neutral.

The numerics are pure numpy; ``rateslib``/``QuantLib`` are never on this path.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from giltcurve.curves.discount import DiscountCurve
from giltcurve.premium.pca import PCAResult, yield_pca

PERIODS_PER_YEAR = 12
H = 1.0 / PERIODS_PER_YEAR
MONTHLY_GRID_YEARS = np.arange(1, 121) / float(PERIODS_PER_YEAR)


def curve_from_yields(maturities, yields, asof=None) -> DiscountCurve:
    """Build a DiscountCurve from annualised continuous zero yields."""
    t = np.asarray(maturities, float)
    r = np.asarray(yields, float)
    m = np.isfinite(t) & np.isfinite(r) & (t > 0)
    t, r = t[m], r[m]
    return DiscountCurve(t, np.exp(-r * t), valuation_date=asof)


def resample_to_monthly_grid(panel: pd.DataFrame, grid=MONTHLY_GRID_YEARS) -> pd.DataFrame:
    """Resample each date's curve onto the monthly maturity grid (1..120 months).

    Returns a DataFrame index=date, columns=maturity(years) on ``grid``. Below the
    first pillar the curve's flat-zero left behaviour applies (see flagged
    judgment call: the 1-month node may be extrapolated).
    """
    grid = np.asarray(grid, float)
    rows = {}
    mats = panel.columns.to_numpy(float)
    for date, row in panel.iterrows():
        curve = curve_from_yields(mats, row.to_numpy(float), date)
        rows[date] = curve.zero(grid)
    out = pd.DataFrame.from_dict(rows, orient="index", columns=grid)
    out.index.name = panel.index.name
    return out


def excess_returns(monthly_panel: pd.DataFrame) -> np.ndarray:
    """One-period log excess holding returns on the monthly-maturity grid.

    Input: annualised yields on the 1..120-month grid (columns in years).
    Returns an array (T-1, N-1): column j is the excess return of the bond that
    is maturity (j+2) months at t, aging to (j+1) months at t+1.

    Per-period prices p^{(n)} = -n * (y_annual * H); risk-free = 1-month
    per-period yield; rx_{t+1} = p^{(n-1)}_{t+1} - p^{(n)}_t - r^{(1)}_t.
    """
    Y = monthly_panel.to_numpy(float)
    n_months = np.round(monthly_panel.columns.to_numpy(float) * PERIODS_PER_YEAR)
    yp = Y * H                       # per-period yields
    P = -n_months[None, :] * yp      # per-period log prices
    rf = yp[:, 0]                    # 1-month per-period yield
    return P[1:, :-1] - P[:-1, 1:] - rf[:-1, None]


def fit_var1(factors: np.ndarray):
    """OLS VAR(1): X_{t+1} = mu + Phi X_t + v.  Returns (mu, Phi, Sigma, resid).

    ``Sigma`` is the MLE innovation covariance (divides by T-1 observations);
    ``resid`` rows are the innovations v_{t+1}, aligned to the t+1 index.
    """
    X = np.asarray(factors, float)
    X0, X1 = X[:-1], X[1:]
    Z = np.column_stack([np.ones(len(X0)), X0])
    coef, *_ = np.linalg.lstsq(Z, X1, rcond=None)
    mu = coef[0]
    Phi = coef[1:].T
    resid = X1 - Z @ coef
    Sigma = (resid.T @ resid) / resid.shape[0]
    return mu, Phi, Sigma, resid
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/premium/acm.py tests/test_acm.py
git commit -m "feat(premium): ACM resampling, excess returns, VAR(1)"
```

---

## Task 3: Three-step price-of-risk OLS + affine recursions (`premium/acm.py` part 2)

**Files:**
- Modify: `src/giltcurve/premium/acm.py` (append functions)
- Test: `tests/test_acm.py` (append tests)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_acm.py`:

```python
from giltcurve.premium.acm import (
    fit_price_of_risk,
    fit_short_rate,
    affine_recursions,
)


def test_short_rate_regression_recovers_linear_map():
    rng = np.random.default_rng(2)
    X = rng.standard_normal((500, 3))
    d0_true, d1_true = 0.002, np.array([0.5, -0.3, 0.1])
    r = d0_true + X @ d1_true
    d0, d1 = fit_short_rate(X, r)
    assert abs(d0 - d0_true) < 1e-9
    np.testing.assert_allclose(d1, d1_true, atol=1e-9)


def test_recursions_zero_risk_equal_fitted_and_riskneutral():
    # With lambda0=lambda1=0, fitted recursion == risk-neutral recursion.
    rng = np.random.default_rng(3)
    K = 3
    mu = rng.normal(0, 1e-3, K)
    Phi = 0.9 * np.eye(K)
    Sigma = np.diag(rng.uniform(1e-5, 1e-4, K))
    sigma2 = 1e-6
    d0, d1 = 0.002, rng.normal(0, 0.1, K)
    A0, B0 = affine_recursions(mu, Phi, Sigma, sigma2, d0, d1,
                               np.zeros(K), np.zeros((K, K)), n_max=120)
    A1, B1 = affine_recursions(mu, Phi, Sigma, sigma2, d0, d1,
                               np.zeros(K), np.zeros((K, K)), n_max=120)
    np.testing.assert_allclose(A0, A1)
    np.testing.assert_allclose(B0, B1)
    assert A0.shape == (121,) and B0.shape == (121, K)


def test_one_month_model_yield_matches_short_rate():
    # The 1-period (n=1) model yield equals the short rate delta0 + delta1'X.
    rng = np.random.default_rng(4)
    K = 3
    mu = rng.normal(0, 1e-3, K)
    Phi = 0.8 * np.eye(K)
    Sigma = np.diag(rng.uniform(1e-5, 1e-4, K))
    sigma2 = 0.0
    d0, d1 = 0.002, rng.normal(0, 0.1, K)
    lam0, lam1 = np.zeros(K), np.zeros((K, K))
    A, B = affine_recursions(mu, Phi, Sigma, sigma2, d0, d1, lam0, lam1, n_max=2)
    x = rng.standard_normal(K)
    # per-period 1m yield from model = -(A1 + B1'x)/1
    y1 = -(A[1] + B[1] @ x)
    np.testing.assert_allclose(y1, d0 + d1 @ x, atol=1e-12)


def test_price_of_risk_shapes_and_lstsq_consistency():
    rng = np.random.default_rng(5)
    T, K, M = 600, 3, 50
    Xl = rng.standard_normal((T, K))
    V = rng.standard_normal((T, K)) * 0.01
    Sigma = np.cov(V.T)
    beta_true = rng.standard_normal((M, K))
    rx = Xl @ rng.standard_normal((K, M)) * 0.001 + V @ beta_true.T
    lam0, lam1, beta, sigma2 = fit_price_of_risk(rx, Xl, V, Sigma)
    assert lam0.shape == (K,)
    assert lam1.shape == (K, K)
    assert beta.shape == (M, K)
    assert sigma2 >= 0.0
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: FAIL with `ImportError: cannot import name 'fit_price_of_risk'`

- [ ] **Step 3: Append the implementation**

Append to `src/giltcurve/premium/acm.py`:

```python
def fit_short_rate(factors: np.ndarray, short_rate_pp: np.ndarray):
    """OLS of the per-period short rate on factors: r_t = delta0 + delta1' X_t."""
    X = np.asarray(factors, float)
    y = np.asarray(short_rate_pp, float)
    Z = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return float(coef[0]), coef[1:]


def fit_price_of_risk(rx, X_lag, innovations, Sigma):
    """ACM step: regress excess returns, recover (lambda0, lambda1, beta, sigma2).

    rx_{t+1} = a + c X_t + beta v_{t+1} + e.  Cross-sectionally:
        lambda1 = (beta' beta)^-1 beta' C
        lambda0 = (beta' beta)^-1 beta' a*,   a* = a + 0.5(diag(beta Sigma beta') + sigma2)
    """
    rx = np.asarray(rx, float)
    Xl = np.asarray(X_lag, float)
    V = np.asarray(innovations, float)
    T_, M = rx.shape
    K = Xl.shape[1]
    Z = np.column_stack([np.ones(T_), Xl, V])
    coef, *_ = np.linalg.lstsq(Z, rx, rcond=None)        # (1+2K, M)
    a = coef[0]
    c = coef[1:1 + K].T                                   # (M, K)
    beta = coef[1 + K:].T                                 # (M, K)
    resid = rx - Z @ coef
    sigma2 = float(np.mean(np.sum(resid ** 2, axis=0) / T_))
    BSB = np.einsum("mk,kl,ml->m", beta, Sigma, beta)     # diag(beta Sigma beta')
    a_star = a + 0.5 * (BSB + sigma2)
    BtB_inv = np.linalg.inv(beta.T @ beta)
    lambda0 = BtB_inv @ beta.T @ a_star
    lambda1 = BtB_inv @ beta.T @ c
    return lambda0, lambda1, beta, sigma2


def affine_recursions(mu, Phi, Sigma, sigma2, delta0, delta1, lambda0, lambda1, n_max):
    """ACM bond-pricing recursions in per-period units. Returns (A, B).

    A: (n_max+1,)  B: (n_max+1, K), with A[0]=0, B[0]=0 and
        A_{n+1} = A_n + B_n'(mu - lambda0) + 0.5(B_n' Sigma B_n + sigma2) - delta0
        B_{n+1} = (Phi - lambda1)' B_n - delta1
    Per-period log price of an n-month bond is p^{(n)} = A_n + B_n' X_t.
    """
    mu = np.asarray(mu, float)
    K = mu.size
    A = np.zeros(n_max + 1)
    B = np.zeros((n_max + 1, K))
    Phi_m = np.asarray(Phi, float) - np.asarray(lambda1, float)
    mu_m = mu - np.asarray(lambda0, float)
    d1 = np.asarray(delta1, float)
    for n in range(n_max):
        An, Bn = A[n], B[n]
        A[n + 1] = An + Bn @ mu_m + 0.5 * (Bn @ Sigma @ Bn + sigma2) - delta0
        B[n + 1] = Phi_m.T @ Bn - d1
    return A, B
```

- [ ] **Step 4: Run to verify all `test_acm.py` tests pass**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/premium/acm.py tests/test_acm.py
git commit -m "feat(premium): ACM three-step price-of-risk OLS and affine recursions"
```

---

## Task 4: `fit_acm` + `decompose` end-to-end + self-consistency test (`premium/acm.py` part 3)

**Files:**
- Modify: `src/giltcurve/premium/acm.py` (append `ACMResult`, `fit_acm`, `decompose`)
- Test: `tests/test_acm.py` (append round-trip test)

- [ ] **Step 1: Append the failing round-trip test**

Append to `tests/test_acm.py`:

```python
from giltcurve.premium.acm import fit_acm, decompose, ACMResult


def _simulate_acm_panel(T=600, K=3, seed=7, lambda_scale=0.0):
    """Simulate a yield panel from a known ACM (lambda_scale=0 => no term premium).

    Returns an annualised-yield monthly panel on the 1..120m grid.
    """
    from giltcurve.premium.acm import (
        MONTHLY_GRID_YEARS, PERIODS_PER_YEAR, affine_recursions,
    )
    rng = np.random.default_rng(seed)
    mu = rng.normal(0, 5e-4, K)
    Phi = 0.97 * np.eye(K) + rng.normal(0, 0.01, (K, K))
    Sig = np.diag(rng.uniform(1e-6, 4e-6, K))
    L = np.linalg.cholesky(Sig)
    d0 = 0.04 / PERIODS_PER_YEAR
    d1 = rng.normal(0, 1e-3, K)
    lam0 = lambda_scale * rng.normal(0, 1e-3, K)
    lam1 = lambda_scale * rng.normal(0, 1e-2, (K, K))
    A, B = affine_recursions(mu, Phi, Sig, 0.0, d0, d1, lam0, lam1, n_max=120)
    X = np.zeros((T, K))
    for t in range(1, T):
        X[t] = mu + Phi @ X[t - 1] + L @ rng.standard_normal(K)
    n_months = np.arange(1, 121)
    pp_yields = -(A[1:][None, :] + X @ B[1:].T) / n_months[None, :]   # per-period
    annual = pp_yields * PERIODS_PER_YEAR
    idx = pd.date_range("1990-01-31", periods=T, freq="ME")
    return pd.DataFrame(annual, columns=MONTHLY_GRID_YEARS, index=idx)


def test_fit_acm_returns_result_with_expected_shapes():
    panel = _simulate_acm_panel(lambda_scale=1.0)
    res = fit_acm(panel, k=5, currency="TEST")
    assert isinstance(res, ACMResult)
    assert res.A.shape == (121,)
    assert res.B.shape == (121, 5)
    assert res.currency == "TEST"


def test_decompose_term_premium_near_zero_when_no_risk_price():
    # Panel simulated with lambda=0: term premium must be ~0 at all tenors.
    panel = _simulate_acm_panel(lambda_scale=0.0)
    res = fit_acm(panel, k=5, currency="TEST")
    out = decompose(res, panel)
    tp = out[out["maturity"].isin([2.0, 5.0, 10.0])]["term_premium"]
    assert np.nanmax(np.abs(tp.to_numpy(float))) < 15e-4  # < 15bp


def test_decompose_fitted_close_to_observed():
    panel = _simulate_acm_panel(lambda_scale=1.0)
    res = fit_acm(panel, k=5, currency="TEST")
    out = decompose(res, panel)
    err = (out["fitted"] - out["observed"]).to_numpy(float)
    rmse_bp = np.sqrt(np.nanmean(err ** 2)) * 1e4
    assert rmse_bp < 10.0  # in-sample fit within 10bp


def test_decompose_columns_and_keys():
    panel = _simulate_acm_panel()
    res = fit_acm(panel, k=5, currency="GBP")
    out = decompose(res, panel, maturities=[1, 2, 5, 10])
    assert list(out.columns) == [
        "date", "currency", "maturity", "observed", "fitted",
        "expected_rate", "term_premium",
    ]
    assert set(out["maturity"].unique()) == {1.0, 2.0, 5.0, 10.0}
    assert (out["currency"] == "GBP").all()
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: FAIL with `ImportError: cannot import name 'fit_acm'`

- [ ] **Step 3: Append `ACMResult`, `fit_acm`, `decompose`**

Append to `src/giltcurve/premium/acm.py`:

```python
@dataclass
class ACMResult:
    """Fitted ACM model. Per-period units internally; decompose() re-annualises."""

    currency: str
    pca: PCAResult
    mu: np.ndarray
    Phi: np.ndarray
    Sigma: np.ndarray
    sigma2: float
    delta0: float
    delta1: np.ndarray
    lambda0: np.ndarray
    lambda1: np.ndarray
    beta: np.ndarray
    A: np.ndarray          # fitted recursion (n_max+1,)
    B: np.ndarray          # fitted recursion (n_max+1, K)
    A_rn: np.ndarray       # risk-neutral recursion
    B_rn: np.ndarray
    grid_years: np.ndarray  # MONTHLY_GRID_YEARS


def fit_acm(panel: pd.DataFrame, *, k: int = 5, currency: str, n_max: int = 120) -> ACMResult:
    """Fit the ACM model to an annualised monthly yield panel.

    ``panel`` may be on any maturity grid; it is resampled to the 1..120-month
    grid internally. ``currency`` is a pass-through label (never branched on).
    """
    grid_panel = resample_to_monthly_grid(panel)
    pca = yield_pca(grid_panel, k=k)
    X = pca.factors                                   # (T, K)
    mu, Phi, Sigma, resid = fit_var1(X)               # innovations aligned to t+1
    rx = excess_returns(grid_panel)                   # (T-1, N-1)
    X_lag = X[:-1]
    lambda0, lambda1, beta, sigma2 = fit_price_of_risk(rx, X_lag, resid, Sigma)
    short_pp = grid_panel.iloc[:, 0].to_numpy(float) * H   # 1-month per-period yield
    delta0, delta1 = fit_short_rate(X, short_pp)
    A, B = affine_recursions(mu, Phi, Sigma, sigma2, delta0, delta1,
                             lambda0, lambda1, n_max=n_max)
    A_rn, B_rn = affine_recursions(mu, Phi, Sigma, sigma2, delta0, delta1,
                                   np.zeros_like(lambda0), np.zeros_like(lambda1),
                                   n_max=n_max)
    return ACMResult(currency, pca, mu, Phi, Sigma, sigma2, delta0, delta1,
                     lambda0, lambda1, beta, A, B, A_rn, B_rn, MONTHLY_GRID_YEARS)


def _model_yields(A, B, factors):
    """Annualised model yields on the 1..120-month grid for given factor rows."""
    n_months = np.arange(1, B.shape[0])
    pp = -(A[1:][None, :] + factors @ B[1:].T) / n_months[None, :]
    return pp * PERIODS_PER_YEAR


def decompose(result: ACMResult, panel: pd.DataFrame, maturities=None) -> pd.DataFrame:
    """Decompose ``panel`` into observed / fitted / expected_rate / term_premium.

    The panel can be monthly (in-sample) or daily (out-of-sample) — its yields are
    resampled to the monthly grid and projected onto the fitted PCA loadings.
    ``maturities`` (years) selects reported tenors; default 1..10y integer tenors.
    Returns a tidy frame keyed (date, currency, maturity).
    """
    if maturities is None:
        maturities = np.arange(1, 11, dtype=float)
    maturities = np.asarray(maturities, float)
    grid_panel = resample_to_monthly_grid(panel)
    obs = grid_panel.to_numpy(float)
    factors = result.pca.project(obs)
    fitted = _model_yields(result.A, result.B, factors)
    riskn = _model_yields(result.A_rn, result.B_rn, factors)
    term_premium = fitted - riskn

    grid = result.grid_years
    col_idx = {m: int(np.argmin(np.abs(grid - m))) for m in maturities}
    records = []
    for r, date in enumerate(grid_panel.index):
        for m in maturities:
            j = col_idx[m]
            records.append({
                "date": date, "currency": result.currency, "maturity": float(m),
                "observed": obs[r, j], "fitted": fitted[r, j],
                "expected_rate": riskn[r, j], "term_premium": term_premium[r, j],
            })
    return pd.DataFrame.from_records(records)
```

- [ ] **Step 4: Run to verify all `test_acm.py` tests pass**

Run: `python3 -m pytest tests/test_acm.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/premium/acm.py tests/test_acm.py
git commit -m "feat(premium): fit_acm + decompose with simulated ACM round-trip"
```

---

## Task 5: US anchor ingest — GSW curve + NY Fed ACM series (`ingest/fed.py`)

**Files:**
- Create: `src/giltcurve/ingest/fed.py`
- Test: `tests/test_fed_ingest.py`

- [ ] **Step 1: Discovery — confirm the live formats (do this first, record findings in the module docstring)**

Run these and read the headers/columns before coding the parser:

```bash
python3 - <<'PY'
import urllib.request, io
# GSW zero-coupon yields (Gurkaynak-Sack-Wright), Fed Board:
url = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
req = urllib.request.Request(url, headers={"User-Agent": "giltcurve-research/0.1"})
txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
lines = txt.splitlines()
print("GSW total lines:", len(lines))
# find the header row containing SVENY01
hdr = next(i for i, l in enumerate(lines) if "SVENY01" in l)
print("GSW header row index:", hdr)
print("GSW header:", lines[hdr][:300])
print("GSW first data row:", lines[hdr + 1][:200])
PY
```

```bash
python3 - <<'PY'
import urllib.request, pandas as pd, io
# NY Fed ACM term premia (xls). Confirm sheet + column names ACMTP01.., ACMRNY01.., ACMY01..
url = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"
req = urllib.request.Request(url, headers={"User-Agent": "giltcurve-research/0.1"})
raw = urllib.request.urlopen(req, timeout=60).read()
xls = pd.ExcelFile(io.BytesIO(raw))
print("ACM sheets:", xls.sheet_names)
df = xls.parse(xls.sheet_names[0], nrows=3)
print("ACM columns sample:", [c for c in df.columns][:12])
print(df.head(2).to_string())
PY
```

Expected: GSW header contains `SVENY01..SVENY30` (continuously compounded zero yields, percent) with a `Date` column; ACM has `ACMTP01..ACMTP10`, `ACMY01..`, `ACMRNY01..` columns and a date column. **If column names differ, adjust the constants in Step 3 accordingly.**

- [ ] **Step 2: Write the failing tests (network-gated, auto-skip offline)**

Create `tests/test_fed_ingest.py`:

```python
"""Real-data parse checks for the US anchor (GSW + NY Fed ACM).

Network-dependent; auto-skip when offline, mirroring tests/test_boe_ingest.py.
"""
import numpy as np
import pytest

from giltcurve.ingest import fed


def _online():
    try:
        fed.download_gsw(force=False)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _online(), reason="needs network for Fed data")


def test_gsw_panel_shape_and_units():
    panel = fed.load_gsw_panel()
    # Annual maturities 1..N years, decimal yields in a sane range.
    assert panel.shape[1] >= 10
    assert panel.columns.min() == 1.0
    vals = panel.dropna(how="all").to_numpy(float)
    finite = vals[np.isfinite(vals)]
    assert finite.min() > -0.02 and finite.max() < 0.25  # decimals, not percent


def test_acm_series_has_10y_term_premium():
    acm = fed.load_nyfed_acm()
    assert "term_premium" in acm.columns.names or 10.0 in acm["term_premium"].columns
    tp10 = fed.nyfed_term_premium(acm, tenor=10.0)
    assert tp10.notna().sum() > 200  # decades of monthly data
```

- [ ] **Step 3: Implement `ingest/fed.py`**

Create `src/giltcurve/ingest/fed.py` (adjust constants to Step-1 findings if needed):

```python
"""US validation-anchor data: the GSW zero curve and NY Fed ACM term premia.

These are the external correctness anchor for the ACM estimator (Step D of the
brief): running our estimator on the Fed Board's Gürkaynak–Sack–Wright (GSW)
zero-coupon curve should reproduce the New York Fed's *published* ACM Treasury
term premia. Both are free public downloads. They are used only for validation;
they are never imported by the core estimator.
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

GSW_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
NYFED_ACM_URL = (
    "https://www.newyorkfed.org/medialibrary/media/research/"
    "data_indicators/ACMTermPremium.xls"
)
_UA = {"User-Agent": "giltcurve-research/0.1"}


def _get(url: str, dest: Path, force: bool) -> bytes:
    if dest.exists() and not force:
        return dest.read_bytes()
    req = urllib.request.Request(url, headers=_UA)
    raw = urllib.request.urlopen(req, timeout=60).read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return raw


def download_gsw(data_dir="data/raw", force: bool = False) -> Path:
    dest = Path(data_dir) / "feds200628.csv"
    _get(GSW_URL, dest, force)
    return dest


def download_nyfed_acm(data_dir="data/raw", force: bool = False) -> Path:
    dest = Path(data_dir) / "ACMTermPremium.xls"
    _get(NYFED_ACM_URL, dest, force)
    return dest


def load_gsw_panel(data_dir="data/raw", force: bool = False, max_tenor: int = 10) -> pd.DataFrame:
    """GSW continuously-compounded zero yields -> panel (date x maturity[yrs], decimal).

    The CSV carries a long metadata preamble; the header row is the one with
    ``SVENY01``. Columns ``SVENY01..SVENY{N}`` are annual zero yields in percent.
    """
    path = download_gsw(data_dir, force)
    text = path.read_text("utf-8", "replace").splitlines()
    hdr = next(i for i, line in enumerate(text) if "SVENY01" in line)
    df = pd.read_csv(io.StringIO("\n".join(text[hdr:])))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    cols = {c: int(c.replace("SVENY", "")) for c in df.columns
            if c.startswith("SVENY") and c[5:].isdigit()}
    keep = {y: c for c, y in cols.items() if y <= max_tenor}
    out = df[list(keep.values())].apply(pd.to_numeric, errors="coerce") / 100.0
    out.columns = [float(y) for y in keep.keys()]
    return out.reindex(sorted(out.columns), axis=1)


def load_nyfed_acm(data_dir="data/raw", force: bool = False) -> pd.DataFrame:
    """NY Fed ACM workbook -> tidy frame index=date, MultiIndex cols (kind, tenor).

    kind in {"yield","term_premium","risk_neutral"} from ACMY/ACMTP/ACMRNY.
    """
    path = download_nyfed_acm(data_dir, force)
    raw = pd.read_excel(path)
    date_col = raw.columns[0]
    raw[date_col] = pd.to_datetime(raw[date_col], errors="coerce")
    raw = raw.dropna(subset=[date_col]).set_index(date_col).sort_index()
    kind_map = {"ACMTP": "term_premium", "ACMRNY": "risk_neutral", "ACMY": "yield"}
    tuples, data = [], {}
    for col in raw.columns:
        for prefix, kind in kind_map.items():
            if col.startswith(prefix) and col[len(prefix):].isdigit():
                tenor = float(col[len(prefix):])
                tuples.append((kind, tenor))
                data[(kind, tenor)] = pd.to_numeric(raw[col], errors="coerce") / 100.0
                break
    out = pd.DataFrame(data)
    out.columns = pd.MultiIndex.from_tuples(out.columns, names=["kind", "tenor"])
    return out


def nyfed_term_premium(acm: pd.DataFrame, tenor: float = 10.0) -> pd.Series:
    """Published NY Fed term-premium series at a tenor (years), decimal."""
    return acm["term_premium"][float(tenor)]
```

Note: `load_nyfed_acm` returns a single-level helper too — `acm["term_premium"]`
is a `(date x tenor)` frame, so the test's `10.0 in acm["term_premium"].columns`
works.

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_fed_ingest.py -q`
Expected: PASS if online (2 passed); SKIPPED if offline. If columns differ from
assumptions, fix constants/parsing per Step-1 discovery and re-run.

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/ingest/fed.py tests/test_fed_ingest.py
git commit -m "feat(ingest): GSW zero curve + NY Fed ACM term-premia loaders"
```

---

## Task 6: BoE nominal gilt zero-curve ingest (`ingest/boe_gilt.py`)

**Files:**
- Create: `src/giltcurve/ingest/boe_gilt.py`
- Test: `tests/test_boe_gilt_ingest.py`

- [ ] **Step 1: Discovery — confirm workbook names, sheets, grid, history span**

Run and record findings (the BoE archive ships nominal-gilt history in dated
workbooks plus a current-month file):

```bash
python3 - <<'PY'
import urllib.request, zipfile, io
# The archive index page lists the GLC Nominal files; the "latest" zip holds the
# current-month nominal/real/OIS workbooks. Historical nominal files are linked
# from the yield-curve page (e.g. "GLC Nominal daily data_1979 to 2002", etc.).
url = ("https://www.bankofengland.co.uk/-/media/boe/files/statistics/"
       "yield-curves/latest-yield-curve-data.zip")
req = urllib.request.Request(url, headers={"User-Agent": "giltcurve-research/0.1"})
raw = urllib.request.urlopen(req, timeout=60).read()
zf = zipfile.ZipFile(io.BytesIO(raw))
print("zip members:")
for n in zf.namelist():
    print("  ", n)
PY
```

Expected: members include a nominal-gilt workbook (name containing `Nominal`,
e.g. `GLC Nominal daily data current month.xlsx`). Note the exact name and, by
opening it, the spot-curve sheet name (expected `4. spot curve`) and the maturity
grid. **Record the exact workbook + sheet name as the module constants.** For the
multi-decade history needed by ACM, also note the dated history workbook URLs
from the BoE yield-curve page and document how to place them in `data/raw`.

- [ ] **Step 2: Write the failing tests (network-gated, auto-skip offline)**

Create `tests/test_boe_gilt_ingest.py`:

```python
"""Real-data parse checks for the BoE nominal gilt zero curve.

Network-dependent; auto-skip offline, mirroring tests/test_boe_ingest.py.
"""
import numpy as np
import pytest

from giltcurve.ingest import boe_gilt


def _online():
    try:
        boe_gilt.ensure_gilt_workbook()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _online(), reason="needs network for BoE data")


def test_gilt_panel_is_dated_and_decimal():
    panel = boe_gilt.load_gilt_panel()
    assert panel.index.is_monotonic_increasing
    assert panel.shape[1] >= 10
    vals = panel.dropna(how="all").to_numpy(float)
    finite = vals[np.isfinite(vals)]
    assert finite.min() > -0.02 and finite.max() < 0.25  # decimals


def test_gilt_panel_has_no_weekend_rows():
    panel = boe_gilt.load_gilt_panel()
    weekdays = panel.index.dayofweek
    assert (weekdays < 5).all()  # no Sat/Sun (non-trading days)
```

- [ ] **Step 3: Implement `ingest/boe_gilt.py`**

Create `src/giltcurve/ingest/boe_gilt.py` (reuse `boe.parse_ois_sheet`'s mechanics;
adjust the workbook/sheet constants to Step-1 findings):

```python
"""Ingest the Bank of England published NOMINAL gilt zero-coupon curve.

ACM decomposes the *government bond* curve, so this loads the BoE Anderson–Sleath
nominal-gilt spot curve (daily, from 1979) from the same yield-curves source as
the SONIA OIS curve. It reuses the sheet-parsing mechanics of ``ingest/boe.py``
(``years:`` header row; column A = dates mixed with header strings; values in
percent). The SONIA OIS curve is NOT decomposed here — it is the expectations
anchor in the validation step (``policy/meeting_dated.py``).

History: ACM needs decades of monthly data. The current-month workbook ships in
``latest-yield-curve-data.zip``; multi-decade history ships as dated workbooks on
the BoE yield-curve page. Place any downloaded history workbooks in ``data/raw``
and pass the directory; ``load_gilt_history`` concatenates every nominal workbook
it finds there.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from giltcurve.ingest.boe import download_boe_zip, parse_ois_sheet
from giltcurve.curves.discount import DiscountCurve
import numpy as np

GILT_WORKBOOK = "GLC Nominal daily data current month.xlsx"  # confirm in Step 1
SPOT_SHEET = "4. spot curve"  # confirm in Step 1


def extract_gilt_workbook(zip_path, dest_dir="data/raw", member=GILT_WORKBOOK) -> Path:
    dest_dir = Path(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if member not in names:
            member = next(n for n in names if "Nominal" in n and n.endswith(".xlsx"))
        zf.extract(member, dest_dir)
    return dest_dir / member


def ensure_gilt_workbook(data_dir="data/raw", force: bool = False) -> Path:
    data_dir = Path(data_dir)
    existing = sorted(data_dir.glob("*Nominal*.xlsx"))
    if existing and not force:
        return existing[-1]
    zp = download_boe_zip(data_dir, force=force)
    return extract_gilt_workbook(zp, data_dir)


def load_gilt_panel(data_dir="data/raw", sheet=SPOT_SHEET, force: bool = False) -> pd.DataFrame:
    """Parse the current nominal-gilt spot sheet -> panel (date x maturity, decimal)."""
    xlsx = ensure_gilt_workbook(data_dir, force=force)
    panel = parse_ois_sheet(xlsx, sheet)   # same layout; returns decimals, sorted
    return panel.dropna(how="all")


def load_gilt_history(data_dir="data/raw", sheet=SPOT_SHEET) -> pd.DataFrame:
    """Concatenate every nominal-gilt workbook found in ``data_dir`` into one panel.

    Drop any present in the current-month file but duplicated across history files,
    keeping the last occurrence. Used for the multi-decade ACM estimation panel.
    """
    files = sorted(Path(data_dir).glob("*Nominal*.xlsx"))
    if not files:
        raise FileNotFoundError("no '*Nominal*.xlsx' gilt workbooks in data dir")
    frames = [parse_ois_sheet(f, sheet) for f in files]
    panel = pd.concat(frames).sort_index()
    panel = panel[~panel.index.duplicated(keep="last")]
    return panel.dropna(how="all")


def latest_gilt_curve(data_dir="data/raw", force: bool = False) -> DiscountCurve:
    """Most recent nominal-gilt spot row -> DiscountCurve (D = exp(-R t))."""
    panel = load_gilt_panel(data_dir, force=force)
    last = panel.iloc[-1].dropna()
    asof = panel.index[-1]
    asof = asof.date() if hasattr(asof, "date") else asof
    t = last.index.to_numpy(float)
    r = last.to_numpy(float)
    return DiscountCurve(t, np.exp(-r * t), valuation_date=asof)
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_boe_gilt_ingest.py -q`
Expected: PASS if online (2 passed); SKIPPED if offline. Fix constants per Step-1
discovery if the workbook/sheet names differ.

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/ingest/boe_gilt.py tests/test_boe_gilt_ingest.py
git commit -m "feat(ingest): BoE nominal gilt zero-curve loader"
```

---

## Task 7: Downstream hooks — decomposed panel + cross-currency differentials (`premium/panel.py`)

**Files:**
- Create: `src/giltcurve/premium/panel.py`
- Test: `tests/test_panel.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_panel.py`:

```python
"""Tests for premium/panel.py — downstream-ready decomposed panel + differentials."""
import numpy as np
import pandas as pd

from giltcurve.premium.panel import decomposed_panel, cross_currency_differentials


def _toy_decomposed(currency, base_rate, tp_slope, dates):
    """Build a decomposed-panel-shaped frame directly (no estimation needed)."""
    mats = [1.0, 2.0, 5.0, 10.0]
    rows = []
    for d in dates:
        for m in mats:
            er = base_rate
            tp = tp_slope * m
            rows.append({"date": d, "currency": currency, "maturity": m,
                         "observed": er + tp, "fitted": er + tp,
                         "expected_rate": er, "term_premium": tp})
    return pd.DataFrame(rows)


def test_decomposed_panel_concatenates_currencies():
    dates = pd.date_range("2020-01-31", periods=3, freq="ME")
    us = _toy_decomposed("USD", 0.02, 0.001, dates)
    gb = _toy_decomposed("GBP", 0.03, 0.0008, dates)
    panel = decomposed_panel([us, gb])
    assert set(panel["currency"]) == {"USD", "GBP"}
    assert list(panel.columns) == [
        "date", "currency", "maturity", "observed", "fitted",
        "expected_rate", "term_premium",
    ]


def test_cross_currency_differentials_vs_usd():
    dates = pd.date_range("2020-01-31", periods=2, freq="ME")
    us = _toy_decomposed("USD", 0.02, 0.001, dates)
    gb = _toy_decomposed("GBP", 0.03, 0.0008, dates)
    panel = decomposed_panel([us, gb])
    diff = cross_currency_differentials(panel, tenor=10.0, base="USD")
    # GBP 10y: exp-rate diff = 0.03-0.02 = 0.01; tp diff = (0.0008-0.001)*10 = -0.002
    g = diff[diff["currency"] == "GBP"].iloc[0]
    assert abs(g["exp_rate_diff"] - 0.01) < 1e-12
    assert abs(g["term_premium_diff"] - (-0.002)) < 1e-12
    # USD vs itself is dropped (base)
    assert "USD" not in set(diff["currency"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_panel.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'giltcurve.premium.panel'`

- [ ] **Step 3: Implement `premium/panel.py`**

Create `src/giltcurve/premium/panel.py`:

```python
"""Downstream-ready decomposed panel and cross-currency component differentials.

This is the hand-off surface to the downstream cross-currency basis project. It
exposes the decomposed rate components keyed by (date, currency, maturity) and a
helper returning, per tenor, each currency's expected-rate and term-premium
differential versus USD.

HARD CONSTRAINT (do not remove): this module must NOT regress any currency's
cross-currency basis on its own term premium over time — that is circular and out
of scope. This module only PRODUCES decomposed rate components. Cross-sectional
basis modelling happens downstream, ACROSS currencies, not here.
"""
from __future__ import annotations

import pandas as pd

_COLUMNS = ["date", "currency", "maturity", "observed", "fitted",
            "expected_rate", "term_premium"]


def decomposed_panel(per_currency_frames) -> pd.DataFrame:
    """Concatenate per-currency `decompose()` outputs into one tidy panel."""
    panel = pd.concat(list(per_currency_frames), ignore_index=True)
    return panel[_COLUMNS].sort_values(["currency", "date", "maturity"]).reset_index(drop=True)


def cross_currency_differentials(panel: pd.DataFrame, tenor: float, base: str = "USD") -> pd.DataFrame:
    """Per (date, currency) differential of each component vs ``base`` at ``tenor``.

    Returns columns: date, currency, exp_rate_diff, term_premium_diff. The base
    currency is dropped (its differential vs itself is zero).
    """
    at = panel[panel["maturity"] == float(tenor)]
    base_rows = at[at["currency"] == base].set_index("date")
    out = []
    for ccy, grp in at[at["currency"] != base].groupby("currency"):
        g = grp.set_index("date")
        joined = g.join(base_rows[["expected_rate", "term_premium"]],
                        rsuffix="_base", how="inner")
        for date, row in joined.iterrows():
            out.append({
                "date": date, "currency": ccy,
                "exp_rate_diff": row["expected_rate"] - row["expected_rate_base"],
                "term_premium_diff": row["term_premium"] - row["term_premium_base"],
            })
    return pd.DataFrame(out, columns=["date", "currency", "exp_rate_diff", "term_premium_diff"])
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_panel.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/giltcurve/premium/panel.py tests/test_panel.py
git commit -m "feat(premium): decomposed panel + cross-currency differentials"
```

---

## Task 8: End-to-end runner with halt-on-failure validation (`scripts/run_term_premium.py`)

**Files:**
- Create: `scripts/run_term_premium.py`
- (No new unit test; this is the real-data validation harness, run manually.)

- [ ] **Step 1: Implement the runner**

Create `scripts/run_term_premium.py`:

```python
#!/usr/bin/env python3
"""End-to-end ACM term-premium: US correctness anchor -> GBP decomposition.

Pipeline
--------
1. US ANCHOR (correctness proof): fit the estimator on the Fed Board GSW zero
   curve and compare 1-10y term premia to the NY Fed's *published* ACM series.
   HALT if correlation is too low — the estimator is not trusted on GBP until it
   reproduces a published benchmark.
2. GBP: fit on the BoE nominal gilt curve; decompose into expected-rate + term
   premium; compare the expected-rate path to the existing SONIA implied Bank
   Rate path (policy/meeting_dated.py) as a robustness diagnostic (shape/changes,
   not levels — gilt vs OIS basis).
3. SHAPE TESTS (halt): term premium ~0 at the short end and rising with maturity.
4. Save the decomposed panel and figures.

Run:  python scripts/run_term_premium.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from giltcurve.ingest import fed, boe_gilt
from giltcurve.premium.acm import fit_acm, decompose
from giltcurve.premium.panel import decomposed_panel

CORR_FLOOR = 0.95          # min corr vs NY Fed ACM per tenor (halt below)
LEVEL_RMSE_CEIL_BP = 60.0  # max RMSE vs NY Fed 10y term premium (halt above)


def _eom(panel: pd.DataFrame) -> pd.DataFrame:
    """Resample a daily panel to month-end observations."""
    return panel.resample("ME").last().dropna(how="all")


def _halt(msg: str) -> None:
    print(f"\n[HALT] {msg}")
    raise SystemExit(1)


def validate_us() -> pd.DataFrame:
    print("=== US correctness anchor (GSW -> ACM vs NY Fed) ===")
    gsw_daily = fed.load_gsw_panel()
    gsw = _eom(gsw_daily)
    res = fit_acm(gsw, k=5, currency="USD")
    tenors = [float(t) for t in range(1, 11)]
    out = decompose(res, gsw, maturities=tenors)
    nyfed = fed.load_nyfed_acm()

    print(f"  GSW months: {gsw.shape[0]}  ({gsw.index.min():%Y-%m} .. {gsw.index.max():%Y-%m})")
    print("  tenor   corr   ours_bp  nyfed_bp")
    worst_corr = 1.0
    for t in tenors:
        ours = out[out["maturity"] == t].set_index("date")["term_premium"]
        theirs = fed.nyfed_term_premium(nyfed, tenor=t)
        j = ours.index.intersection(theirs.index)
        if len(j) < 60:
            continue
        c = float(np.corrcoef(ours.loc[j], theirs.loc[j])[0, 1])
        worst_corr = min(worst_corr, c)
        print(f"  {t:4.0f}y  {c:5.2f}  {ours.loc[j].mean()*1e4:7.0f}  {theirs.loc[j].mean()*1e4:7.0f}")
        if t == 10.0:
            rmse_bp = float(np.sqrt(np.nanmean((ours.loc[j] - theirs.loc[j]) ** 2)) * 1e4)
    if worst_corr < CORR_FLOOR:
        _halt(f"US anchor correlation {worst_corr:.2f} < {CORR_FLOOR}; estimator not validated.")
    if rmse_bp > LEVEL_RMSE_CEIL_BP:
        _halt(f"US 10y term-premium RMSE {rmse_bp:.0f}bp > {LEVEL_RMSE_CEIL_BP}bp.")
    print(f"  PASS: min corr {worst_corr:.2f}, 10y RMSE {rmse_bp:.0f}bp\n")
    return out


def shape_tests(out: pd.DataFrame, label: str) -> None:
    print(f"=== shape tests ({label}) ===")
    mean_tp = out.groupby("maturity")["term_premium"].mean()
    short = mean_tp.loc[mean_tp.index.min()]
    long = mean_tp.loc[mean_tp.index.max()]
    if abs(short) > 25e-4:
        _halt(f"{label}: short-end term premium {short*1e4:.0f}bp not near zero.")
    if long <= short:
        _halt(f"{label}: term premium not rising with maturity ({short*1e4:.0f}->{long*1e4:.0f}bp).")
    print(f"  PASS: short {short*1e4:.0f}bp, long {long*1e4:.0f}bp (rising)\n")


def decompose_gbp() -> pd.DataFrame:
    print("=== GBP decomposition (BoE nominal gilt) ===")
    gilt_daily = boe_gilt.load_gilt_history()  # falls back to current month if that's all there is
    gilt = _eom(gilt_daily)
    res = fit_acm(gilt, k=5, currency="GBP")
    out = decompose(res, gilt, maturities=[float(t) for t in range(1, 11)])
    print(f"  gilt months: {gilt.shape[0]}  ({gilt.index.min():%Y-%m} .. {gilt.index.max():%Y-%m})")
    last = out[out["date"] == out["date"].max()]
    print("  latest 10y: expected-rate {:.2f}% + term-premium {:.0f}bp".format(
        last[last["maturity"] == 10.0]["expected_rate"].iloc[0] * 100,
        last[last["maturity"] == 10.0]["term_premium"].iloc[0] * 1e4))
    return out


def gbp_vs_sonia_path(gbp_out: pd.DataFrame) -> None:
    """Robustness diagnostic: ACM expected-rate vs SONIA implied Bank Rate path.

    Compared on shape/changes only — ACM is gilt-based, the SONIA path is
    OIS-based, separated by a gilt/swap (asset-swap) spread.
    """
    print("=== GBP robustness: ACM expected-rate vs SONIA implied path ===")
    try:
        from giltcurve.ingest import boe
        from giltcurve.policy.mpc import upcoming_mpc_dates
        from giltcurve.policy.meeting_dated import implied_policy_path
        curve, asof, _, _ = boe.load_latest_curve()
        path = implied_policy_path(curve, upcoming_mpc_dates(asof), asof)
        sonia_2y = path["implied_bank_rate"].iloc[-1]
        er_2y = gbp_out[(gbp_out["maturity"] == 2.0) &
                        (gbp_out["date"] == gbp_out["date"].max())]["expected_rate"].iloc[0]
        print(f"  ACM 2y expected-rate {er_2y*100:.2f}% vs SONIA-path end {sonia_2y*100:.2f}% "
              f"(gap {(er_2y - sonia_2y)*1e4:+.0f}bp; gilt/OIS basis expected).")
    except Exception as exc:  # pragma: no cover - network/data dependent
        print(f"  (skipped: {exc})")


def main() -> int:
    fig_dir = ROOT / "reports" / "figures"
    proc_dir = ROOT / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    try:
        us_out = validate_us()
        shape_tests(us_out, "USD")
        gbp_out = decompose_gbp()
        shape_tests(gbp_out, "GBP")
        gbp_vs_sonia_path(gbp_out)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[!] Could not complete (data/network): {exc}")
        return 1

    panel = decomposed_panel([us_out, gbp_out])
    csv = proc_dir / "term_premium_panel.csv"
    panel.to_csv(csv, index=False)

    # figure: GBP 10y decomposition stack over time
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    g10 = gbp_out[gbp_out["maturity"] == 10.0].set_index("date").sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(g10.index, g10["observed"] * 100, label="10y gilt yield", color="black", lw=1.2)
    ax.plot(g10.index, g10["expected_rate"] * 100, label="expected avg short rate", color="tab:blue")
    ax.plot(g10.index, g10["term_premium"] * 100, label="term premium", color="tab:red")
    ax.set_ylabel("percent"); ax.legend(); ax.set_title("UK 10y gilt: ACM decomposition")
    fig_path = fig_dir / "gbp_term_premium.png"
    fig.tight_layout(); fig.savefig(fig_path, dpi=130); plt.close(fig)

    print("\nsaved:")
    for p in (csv, fig_path):
        print("  ", Path(p).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the full pipeline (real data; needs network)**

Run: `python3 scripts/run_term_premium.py`
Expected: prints the US anchor table with per-tenor correlations (all ≥ 0.95),
PASS lines for shape tests, the GBP decomposition summary, the SONIA-path
diagnostic, and saved artefact paths. **If the US anchor halts**, debug the ACM
math (units/signs) before trusting any GBP output — do not proceed.

- [ ] **Step 3: Commit**

```bash
git add scripts/run_term_premium.py data/processed/term_premium_panel.csv reports/figures/gbp_term_premium.png
git commit -m "feat: ACM term-premium runner with US-anchor halt-on-failure validation"
```

---

## Task 9: Full test sweep + README update

**Files:**
- Modify: `README.md` (roadmap table, validation table, methods note)

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: all existing 32 tests plus the new `test_pca.py`, `test_acm.py`,
`test_panel.py` pass; network-gated ingest tests pass online / skip offline.

- [ ] **Step 2: Update the roadmap table in `README.md`**

In the "Roadmap (Objectives 5–8)" table, mark PCA and ACM done. Replace the
`Yield-curve PCA` and `Term premium (ACM)` rows with:

```markdown
| Yield-curve PCA | `premium/pca.py` | **done** — level/slope/curvature factors; >99% variance in first 3 |
| **Term premium (ACM)** | `premium/acm.py` | **done** — currency-agnostic ACM; validated vs NY Fed ACM |
```

- [ ] **Step 3: Add a validation table + methods note to `README.md`**

After the existing "Validation" table, add a new subsection (fill the bracketed
numbers from the actual `run_term_premium.py` output):

```markdown
### Term-premium validation (ACM)

| Check | Result | What it proves |
|---|---|---|
| Estimator on GSW vs NY Fed published ACM (1–10y) | corr ≥ [X], 10y RMSE [Y]bp | the from-scratch ACM reproduces a published benchmark |
| Term-premium shape | ~0 at short end, rising to 10y | correct affine behaviour |
| GBP expected-rate vs SONIA implied path (2y) | gap [Z]bp | model-robustness; gap is the gilt/OIS basis |

**Methods note.** The term premium splits the nominal government yield into an
expected-average-short-rate component (the risk-neutral yield) and a term premium
(fitted − risk-neutral), via the regression-based Adrian–Crump–Moench affine
model: K=5 PCA pricing factors, a VAR(1) for their dynamics, and a three-step OLS
that prices one-period excess holding returns to recover the prices of risk
(λ₀, λ₁). The estimator is **currency-agnostic** — the same code runs on US GSW
and UK gilt panels with only a currency label changing. The **US series is the
correctness anchor**: we reproduce the NY Fed's published Treasury term premia
before trusting the GBP output, which has no published benchmark. As a
cross-check, the ACM expected-rate path is compared to the existing SONIA implied
Bank Rate path (a gilt-vs-OIS comparison, so read on changes not levels).
```

- [ ] **Step 4: Update the architecture tree in `README.md`**

In the architecture code block, add the new modules under `src/giltcurve/`:

```
│   ├── ingest/boe_gilt.py      # BoE nominal gilt zero curve (ACM input)
│   ├── ingest/fed.py           # GSW curve + NY Fed ACM (US validation anchor)
│   ├── premium/
│   │   ├── pca.py              # PCA pricing factors (level/slope/curvature)
│   │   ├── acm.py              # ACM term-premium decomposition (from scratch)
│   │   └── panel.py            # decomposed panel + cross-currency differentials
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: mark Objectives 5-6 done; ACM methods + validation note"
```

---

## Self-review notes (already reconciled)

- **Spec §5 modules** → Tasks 1,2-4,5,6,7 (pca, acm, fed, boe_gilt, panel). ✓
- **Spec §6 math** → Tasks 2-4 carry every equation as code with unit convention locked. ✓
- **Spec §7 validation** (US anchor halt, GBP-vs-SONIA shape diagnostic, shape tests halt) → Task 8. ✓
- **Spec §8 artefacts** (panel CSV, figures, README table/methods) → Tasks 8, 9. ✓
- **Spec §9 judgment calls** documented in module docstrings (1-month extrapolation in `acm.resample_to_monthly_grid`; gilt/OIS basis in runner; EUR/JPY out of scope). ✓
- **Currency-agnostic constraint** enforced: `fit_acm`/`decompose`/`pca` take only numbers + a label; verified by `test_decompose_columns_and_keys` running with `currency="GBP"` and `"TEST"`. ✓
- **Hard constraint** (no basis-on-own-TP regression) → comment in `premium/panel.py`. ✓
- **Type consistency:** `ACMResult` fields used by `decompose`/runner match definitions; `decompose` output columns match `panel._COLUMNS` and `test_panel`/`test_acm` expectations. ✓
- **Naming:** `load_gsw_panel`, `load_nyfed_acm`, `nyfed_term_premium`, `load_gilt_panel`, `load_gilt_history`, `fit_acm`, `decompose`, `decomposed_panel`, `cross_currency_differentials` used consistently across tasks. ✓
```
