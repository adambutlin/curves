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
