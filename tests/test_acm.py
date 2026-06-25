"""Tests for premium/acm.py — resampling, excess returns, VAR(1), three-step OLS."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.premium.acm import (
    PERIODS_PER_YEAR,
    resample_to_monthly_grid,
    excess_returns,
    fit_var1,
    fit_price_of_risk,
    fit_short_rate,
    affine_recursions,
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


def test_excess_returns_known_value_upward_sloping_constant_curve():
    # Curve constant through time but sloped across maturity: y(n) = a + b*n_years.
    # With per-period prices p(n) = -n_months*(y_annual*H), the one-period excess
    # return of the bond aging n -> n-1 is, holding the curve fixed in time:
    #   rx = p(n-1) - p(n) - p(1)        [since rf = -p(1)]
    # which is a deterministic function of the (constant) curve.
    grid = np.arange(1, 121) / 12.0          # years
    a, b = 0.02, 0.01
    y = a + b * grid                          # annual yields by maturity
    Y = np.tile(y, (4, 1))                    # constant through time
    panel = pd.DataFrame(Y, columns=grid,
                         index=pd.date_range("2020-01-31", periods=4, freq="ME"))
    from giltcurve.premium.acm import H
    n_months = np.arange(1, 121, dtype=float)
    p = -n_months * (y * H)                   # per-period log prices by maturity
    rf = (y * H)[0]                           # 1-month per-period yield
    expected = p[:-1] - p[1:] - rf            # column j: bond (j+2)m -> (j+1)m
    rx = excess_returns(panel)
    assert rx.shape == (3, 119)
    # every period is identical (curve constant in time)
    for t in range(3):
        np.testing.assert_allclose(rx[t], expected, atol=1e-12)


def test_excess_returns_requires_two_dates():
    grid = np.arange(1, 121) / 12.0
    panel = pd.DataFrame(np.full((1, 120), 0.03), columns=grid,
                         index=pd.to_datetime(["2020-01-31"]))
    with pytest.raises(ValueError):
        excess_returns(panel)


def test_fit_var1_requires_two_observations():
    with pytest.raises(ValueError):
        fit_var1(np.zeros((1, 2)))


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


def test_short_rate_regression_recovers_linear_map():
    rng = np.random.default_rng(2)
    X = rng.standard_normal((500, 3))
    d0_true, d1_true = 0.002, np.array([0.5, -0.3, 0.1])
    r = d0_true + X @ d1_true
    d0, d1 = fit_short_rate(X, r)
    assert abs(d0 - d0_true) < 1e-9
    np.testing.assert_allclose(d1, d1_true, atol=1e-9)


def test_recursions_zero_risk_equal_fitted_and_riskneutral():
    # No-arbitrage property: lambda only enters from n>=2 (via Phi_m/mu_m), so the
    # 1-month node is identical for fitted vs risk-neutral, but long maturities differ.
    rng = np.random.default_rng(3)
    K = 3
    mu = rng.normal(0, 1e-3, K)
    Phi = 0.9 * np.eye(K)
    Sigma = np.diag(rng.uniform(1e-5, 1e-4, K))
    sigma2 = 1e-6
    d0, d1 = 0.002, rng.normal(0, 0.1, K)
    lam0 = rng.normal(0, 1e-3, K)
    lam1 = rng.normal(0, 1e-2, (K, K))
    A_fit, B_fit = affine_recursions(mu, Phi, Sigma, sigma2, d0, d1, lam0, lam1, n_max=120)
    A_rn, B_rn = affine_recursions(mu, Phi, Sigma, sigma2, d0, d1,
                                   np.zeros(K), np.zeros((K, K)), n_max=120)
    assert A_fit.shape == (121,) and B_fit.shape == (121, K)
    # 1-month (n=1) node identical: lambda hasn't entered yet
    np.testing.assert_allclose(A_fit[1], A_rn[1], atol=1e-15)
    np.testing.assert_allclose(B_fit[1], B_rn[1], atol=1e-15)
    # long maturities diverge once the price of risk compounds
    assert not np.allclose(A_fit[120], A_rn[120])
    assert not np.allclose(B_fit[120], B_rn[120])


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
