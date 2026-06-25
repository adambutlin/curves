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

    Returns a DataFrame index=date, columns=maturity(years) on ``grid``.
    Below the first pillar, DiscountCurve's t=0 anchor makes interpolation
    equivalent to holding the zero RATE flat at the first pillar (not flat-forward),
    so a sub-pillar node like 1-month is effectively extrapolated when the input
    panel's shortest tenor exceeds 1 month (a flagged judgment call).
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
    if Y.shape[0] < 2:
        raise ValueError("excess_returns needs at least 2 observation dates")
    n_months = np.arange(1, monthly_panel.shape[1] + 1, dtype=float)
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
    if X.shape[0] < 2:
        raise ValueError("fit_var1 needs at least 2 observations")
    X0, X1 = X[:-1], X[1:]
    Z = np.column_stack([np.ones(len(X0)), X0])
    coef, *_ = np.linalg.lstsq(Z, X1, rcond=None)
    mu = coef[0]
    Phi = coef[1:].T
    resid = X1 - Z @ coef
    Sigma = (resid.T @ resid) / resid.shape[0]
    return mu, Phi, Sigma, resid


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
