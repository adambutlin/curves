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
