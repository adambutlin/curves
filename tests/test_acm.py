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
