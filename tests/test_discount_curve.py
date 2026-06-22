"""Tests for the DiscountCurve object and forward/zero extraction.

Key invariants:
  * a flat continuously-compounded curve has zero == forward == r everywhere;
  * log-linear interpolation in the discount factor is equivalent to a
    piecewise-constant instantaneous forward (the OIS market standard);
  * discount factors start at 1.0 and are monotonically decreasing for r > 0.
"""
import numpy as np
import pytest

from giltcurve.curves.discount import DiscountCurve


def _flat_curve(r=0.04, tmax=30, n=61):
    t = np.linspace(tmax / (n - 1), tmax, n - 1)
    return DiscountCurve(t, np.exp(-r * t)), r


def test_df_at_zero_is_one():
    curve, _ = _flat_curve()
    assert curve.df(0.0) == pytest.approx(1.0)


def test_flat_curve_zero_rate_recovers_r():
    curve, r = _flat_curve()
    for t in [0.5, 1.0, 3.7, 10.0, 25.0]:
        assert curve.zero(t) == pytest.approx(r, abs=1e-12)


def test_flat_curve_forward_recovers_r():
    curve, r = _flat_curve()
    assert curve.forward(2.0, 5.0) == pytest.approx(r, abs=1e-12)
    assert curve.inst_forward(7.3) == pytest.approx(r, abs=1e-7)


def test_log_linear_interp_is_piecewise_flat_forward():
    # Two nodes only: the forward between any sub-interval must equal the
    # single node-to-node forward (constant instantaneous forward).
    t = np.array([1.0, 2.0])
    df = np.array([np.exp(-0.03 * 1.0), np.exp(-0.045 * 2.0)])
    curve = DiscountCurve(t, df)
    f_full = curve.forward(1.0, 2.0)
    f_sub = curve.forward(1.2, 1.8)
    assert f_sub == pytest.approx(f_full, abs=1e-12)


def test_discount_factors_monotone_decreasing():
    curve, _ = _flat_curve()
    ts = np.linspace(0.1, 30, 50)
    dfs = curve.df(ts)
    assert np.all(np.diff(dfs) < 0)
    assert np.all(dfs <= 1.0)
