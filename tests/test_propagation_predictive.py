"""Propagation tests on simulated markets with a known answer."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation.predictive import (
    PREMIUM_IDX, curve_controls, forward_changes, impact_on, ols_nw,
    premium_contribution, propagation_ratio_test, reduced_form_test,
    structural_split_test,
)

B_TRUE = np.array([
    [3.0, 4.0, 1.0, -1.0],
    [3.0, 3.0, 2.0, -2.0],
    [2.0, 2.0, 3.0, -3.0],
    [0.8, -0.4, -0.6, -0.7],
])


def _market(T=20000, continuation=0.3, seed=0):
    """Daily moves u = B eps; the premium part of the 10y move continues next day."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal((T, 4))
    U = eps @ B_TRUE.T
    b10 = B_TRUE[2]
    dy = U.copy()
    tp = premium_contribution(eps, b10)
    dy[1:, 2] += continuation * tp[:-1]
    idx = pd.bdate_range("1990-01-01", periods=T)
    lv = 4.0 + np.cumsum(dy[:, :3], axis=0) / 100.0
    panel = pd.DataFrame({"y2": lv[:, 0], "y5": lv[:, 1], "y10": lv[:, 2],
                          "dy2": dy[:, 0], "dy5": dy[:, 1], "dy10": dy[:, 2], "req": dy[:, 3]},
                         index=idx)
    return panel, eps, U


def test_forward_change_excludes_the_day_t_move_and_controls_are_lagged():
    panel, _, _ = _market(T=60)
    r = forward_changes(panel, horizons=(1, 5))
    lv = panel["y10"] * 100
    assert r[("y10", 5)].iloc[10] == pytest.approx(lv.iloc[15] - lv.iloc[10])
    assert np.isnan(r[("y10", 5)].iloc[-1])
    Z = curve_controls(panel)
    assert Z["mom20"].iloc[30] == pytest.approx(lv.iloc[29] - lv.iloc[9])
    assert Z["vol20"].iloc[30] == pytest.approx(panel["dy10"].iloc[10:30].std())


def test_newey_west_matches_ols_errors_when_errors_are_iid():
    rng = np.random.default_rng(5)
    X = np.column_stack([np.ones(20000), rng.standard_normal(20000)])
    y = X @ np.array([0.5, 2.0]) + rng.standard_normal(20000)
    beta, V, _ = ols_nw(y, X, lags=5)
    assert beta == pytest.approx([0.5, 2.0], abs=0.03)
    assert np.sqrt(V[1, 1]) == pytest.approx(1 / np.sqrt(20000), rel=0.1)


def _args(panel, U):
    r = forward_changes(panel, horizons=(1,))[("y10", 1)].to_numpy()
    Z = curve_controls(panel).to_numpy()
    return r, panel["dy10"].to_numpy(), Z


def test_origin_dependent_propagation_is_detected_by_all_three_tests():
    panel, eps, U = _market()
    r, own, Z = _args(panel, U)
    a = reduced_form_test(r, own, U, Z, "y10", 1)
    assert a["p"] < 1e-6
    b = propagation_ratio_test(r, eps, impact_on(B_TRUE, "y10"), Z, 1)
    pi = b["pi"]
    assert pi[PREMIUM_IDX] == pytest.approx([0.3, 0.3], abs=0.03)
    assert pi[[0, 1]] == pytest.approx([0.0, 0.0], abs=0.03)
    assert b["p_equal_pi"] < 1e-6
    c = structural_split_test(r, own, premium_contribution(eps, B_TRUE[2]), Z, 1)
    assert c["kappa"] == pytest.approx(0.3, abs=0.04)
    assert c["t_kappa"] > 10
    assert c["incr_r2"] > 0.01


def test_no_propagation_means_no_rejection():
    panel, eps, U = _market(continuation=0.0, seed=7)
    r, own, Z = _args(panel, U)
    assert reduced_form_test(r, own, U, Z, "y10", 1)["p"] > 0.01
    b = propagation_ratio_test(r, eps, impact_on(B_TRUE, "y10"), Z, 1)
    assert np.abs(b["pi"]).max() < 0.03
    assert b["p_equal_pi"] > 0.01


def test_slope_impact_is_the_10y_minus_2y_row():
    np.testing.assert_allclose(impact_on(B_TRUE, "slope"), B_TRUE[2] - B_TRUE[0])
    many = np.stack([B_TRUE, 2 * B_TRUE])
    np.testing.assert_allclose(impact_on(many, "y2"), many[:, 0, :])


def test_size_test_detects_continuation_of_large_news_only():
    from giltcurve.propagation.predictive import EXPECTATIONS_IDX, large_part, size_split_test
    rng = np.random.default_rng(11)
    T = 30000
    eps = rng.standard_normal((T, 4)) * np.where(rng.random((T, 1)) < 0.05, 3.0, 1.0)
    U = eps @ B_TRUE.T
    b10 = B_TRUE[2]
    c_eh = eps[:, EXPECTATIONS_IDX] @ b10[EXPECTATIONS_IDX]
    c_tp = premium_contribution(eps, b10)
    big_eh = large_part(c_eh, c_eh.std())
    big_tp = large_part(c_tp, c_tp.std())
    dy = U.copy()
    dy[1:, 2] += 0.4 * big_eh[:-1]                     # only large policy news continues
    idx = pd.bdate_range("1990-01-01", periods=T)
    lv = 4.0 + np.cumsum(dy[:, :3], axis=0) / 100.0
    panel = pd.DataFrame({"y2": lv[:, 0], "y5": lv[:, 1], "y10": lv[:, 2], "dy2": dy[:, 0],
                          "dy5": dy[:, 1], "dy10": dy[:, 2], "req": dy[:, 3]}, index=idx)
    r, own, Z = _args(panel, U)
    out = size_split_test(r, own, c_tp, big_eh, big_tp, Z, 1)
    assert out["lambda_eh"] == pytest.approx(0.4, abs=0.08)
    assert out["t_eh"] > 5
    assert abs(out["t_tp"]) < 3
    assert out["incr_r2"] > 0
    assert 0 < out["large_eh_days"] < 0.2 * T
