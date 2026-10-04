"""Regime-dependent identification: real-time regimes and regime-specific shocks."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation.identification import restriction_matrix
from giltcurve.propagation.regimes import (
    COMOVE, HEDGE, regime_identified_sets, regime_indicator,
    regime_premium_contribution, regime_shocks,
)

B_HEDGE = np.array([[3.0, 4.0, 1.0, -1.0], [3.0, 3.0, 2.0, -2.0],
                    [2.0, 2.0, 3.0, -3.0], [0.8, -0.4, -0.2, -0.9]])
B_COMOVE = np.array([[3.0, 4.0, 1.0, -1.0], [3.0, 3.0, 2.0, -2.0],
                     [2.0, 2.0, 3.0, -3.0], [0.2, -0.6, -0.9, -0.2]])


def _two_regime_market(T=6000, seed=0):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal((T, 4))
    first = np.arange(T) < T // 2
    U = np.where(first[:, None], eps @ B_HEDGE.T, eps @ B_COMOVE.T)
    idx = pd.bdate_range("2000-01-03", periods=T)
    panel = pd.DataFrame({"dy2": U[:, 0], "dy5": U[:, 1], "dy10": U[:, 2], "req": U[:, 3]},
                         index=idx)
    return panel, U, eps


def test_regime_uses_only_past_days():
    panel, _, _ = _two_regime_market()
    reg = regime_indicator(panel, window=250)
    assert reg.iloc[:250].isna().all() and reg.iloc[251:].notna().all()
    altered = panel.copy()
    altered.iloc[3000:, :] *= -1.0                  # rewrite day 3000 onwards
    reg2 = regime_indicator(altered, window=250)
    pd.testing.assert_series_equal(reg.iloc[:3001], reg2.iloc[:3001])


def test_regimes_track_the_sign_of_the_stock_bond_correlation():
    panel, _, _ = _two_regime_market()
    reg = regime_indicator(panel, window=250).to_numpy()
    # Hedge DGP: corr(dy10, req) > 0; co-movement DGP: < 0.
    assert np.nanmean(reg[400:2900] == HEDGE) > 0.95
    assert np.nanmean(reg[3400:] == COMOVE) > 0.95


def test_each_regime_gets_its_own_valid_decomposition_and_shocks():
    panel, U, eps = _two_regime_market()
    reg = np.where(np.arange(len(U)) < len(U) // 2, HEDGE, COMOVE)
    sets = regime_identified_sets(U, reg, 50, np.random.default_rng(1))
    for R, Btrue in ((HEDGE, B_HEDGE), (COMOVE, B_COMOVE)):
        S = sets[R].Sigma
        np.testing.assert_allclose(sets[R].B @ np.swapaxes(sets[R].B, 1, 2), S, atol=1e-8)
        np.testing.assert_allclose(S.mean(0), Btrue @ Btrue.T, rtol=0.1, atol=0.3)
        sat = restriction_matrix(np.swapaxes(sets[R].B, 1, 2))
        assert sat[:, np.arange(4), np.arange(4)].all()
    e = regime_shocks(U, reg, sets, 0)
    m = reg == COMOVE
    np.testing.assert_allclose(e[m] @ sets[COMOVE].B[0].T, U[m], atol=1e-9)
    c = regime_premium_contribution(U, reg, sets, 0, "y10")
    b = sets[HEDGE].B[0][2]
    np.testing.assert_allclose(c[~m], e[~m][:, [2, 3]] @ b[[2, 3]], atol=1e-9)


def test_too_few_days_in_a_regime_is_an_error():
    _, U, _ = _two_regime_market(T=400)
    reg = np.full(len(U), HEDGE)
    reg[:10] = COMOVE
    with pytest.raises(ValueError):
        regime_identified_sets(U, reg, 10, np.random.default_rng(2))
