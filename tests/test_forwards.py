"""Tests for the forward/zero reporting layer (Step 3 deliverable tables)."""
import numpy as np

from giltcurve.curves.discount import DiscountCurve
from giltcurve.curves.forwards import forward_table, one_period_forward


def _flat(r=0.04, tmax=30, n=60):
    t = np.linspace(tmax / n, tmax, n)
    return DiscountCurve(t, np.exp(-r * t)), r


def test_forward_table_has_expected_columns_and_length():
    curve, _ = _flat()
    tbl = forward_table(curve, [1, 2, 5, 10])
    assert list(tbl.columns) == ["maturity", "discount_factor", "zero_rate", "inst_forward"]
    assert len(tbl) == 4


def test_flat_curve_zero_equals_forward_equals_r():
    curve, r = _flat()
    tbl = forward_table(curve, [0.5, 1, 3, 7, 15])
    np.testing.assert_allclose(tbl["zero_rate"], r, atol=1e-9)
    np.testing.assert_allclose(tbl["inst_forward"], r, atol=1e-6)


def test_one_period_forward_matches_curve_forward():
    curve, _ = _flat()
    assert one_period_forward(curve, 2.0, tenor=1.0) == curve.forward(2.0, 3.0)
