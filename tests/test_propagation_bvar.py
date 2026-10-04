"""The Minnesota BVAR: design matrix, shrinkage, and posterior concentration."""
import numpy as np
import pytest

from giltcurve.propagation.bvar import design, fit_bvar


def _simulate_var1(A1, c, Sigma, T, seed=0):
    rng = np.random.default_rng(seed)
    n = len(c)
    L = np.linalg.cholesky(Sigma)
    Y = np.zeros((T, n))
    for t in range(1, T):
        Y[t] = c + A1 @ Y[t - 1] + L @ rng.standard_normal(n)
    return Y


A1 = np.array([[0.3, 0.1, 0.0], [0.0, -0.2, 0.05], [0.1, 0.0, 0.1]])
C = np.array([0.1, -0.05, 0.0])
SIG = np.array([[1.0, 0.5, 0.2], [0.5, 2.0, -0.3], [0.2, -0.3, 0.5]])


def test_design_stacks_constant_then_lags_in_order():
    Y = np.arange(12, dtype=float).reshape(6, 2)
    Yt, X = design(Y, 2)
    assert Yt.shape == (4, 2) and X.shape == (4, 5)
    np.testing.assert_array_equal(X[0], [1, 2, 3, 0, 1])   # [1, Y_{t-1}, Y_{t-2}] at t=2
    np.testing.assert_array_equal(Yt[0], Y[2])


def test_posterior_recovers_a_known_var_in_a_long_sample():
    Y = _simulate_var1(A1, C, SIG, 20000)
    post = fit_bvar(Y, p=1, lam=0.2)
    np.testing.assert_allclose(post.A_hat[1:].T, A1, atol=0.03)
    np.testing.assert_allclose(post.A_hat[0], C, atol=0.03)
    np.testing.assert_allclose(post.sigma_mean, SIG, rtol=0.05, atol=0.03)


def test_tight_prior_shrinks_lag_coefficients_toward_zero():
    Y = _simulate_var1(A1, C, SIG, 300, seed=1)
    loose = fit_bvar(Y, p=1, lam=10.0)
    tight = fit_bvar(Y, p=1, lam=0.01)
    assert np.abs(tight.A_hat[1:]).max() < 0.1 * np.abs(loose.A_hat[1:]).max()


def test_draws_are_centred_on_the_posterior_and_covariances_are_valid():
    Y = _simulate_var1(A1, C, SIG, 5000, seed=2)
    post = fit_bvar(Y, p=1)
    A, S = post.draw(400, np.random.default_rng(3))
    assert A.shape == (400, 4, 3) and S.shape == (400, 3, 3)
    np.testing.assert_allclose(A.mean(0), post.A_hat, atol=0.01)
    np.testing.assert_allclose(S.mean(0), post.sigma_mean, rtol=0.03, atol=0.01)
    assert np.all(np.linalg.eigvalsh(S) > 0)
    resid = post.residuals()
    assert resid.shape == post.Y.shape
    assert resid.mean(0) == pytest.approx(np.zeros(3), abs=0.05)
