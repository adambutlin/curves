"""Tests for the SONIA OIS bootstrap (par swap quotes -> discount factors).

OIS convention used here: annual fixed payments, ACT/365F (tau_i = 1 on an
integer-year grid), with the compounded-SONIA floating leg valued as
PV_float = 1 - D(T) on the collateral-discount curve. The par rate is then

    p_N = (1 - D(t_N)) / sum_i tau_i D(t_i).

The bootstrap is the exact algebraic inverse, so it must (a) reprice its own
inputs to zero and (b) round-trip arbitrary discount factors to machine
precision.
"""
import numpy as np
import pytest

from giltcurve.curves.discount import DiscountCurve
from giltcurve.curves.ois_bootstrap import par_ois_rate, bootstrap_ois


def _curve_from_zero(zero_fn, tenors):
    t = np.asarray(tenors, float)
    return DiscountCurve(t, np.exp(-zero_fn(t) * t))


def test_flat_par_curve_gives_geometric_discount_factors():
    # A flat par OIS curve at p implies D_n = (1+p)^-n (annual ACT/365F).
    p = 0.05
    tenors = np.arange(1, 11)
    curve = bootstrap_ois(tenors, np.full(tenors.size, p))
    expected = (1 + p) ** (-tenors.astype(float))
    np.testing.assert_allclose(curve.df(tenors), expected, atol=1e-13)


def test_flat_par_curve_has_flat_continuous_zero():
    p = 0.05
    tenors = np.arange(1, 11)
    curve = bootstrap_ois(tenors, np.full(tenors.size, p))
    z = curve.zero(tenors)
    np.testing.assert_allclose(z, np.log(1 + p), atol=1e-13)


def test_bootstrap_reprices_input_par_rates():
    # Build par rates from a humped zero curve, bootstrap, then re-price the
    # same swaps off the bootstrapped curve: must recover the inputs exactly.
    tenors = np.arange(1, 16)
    zero_fn = lambda t: 0.045 + 0.004 * np.exp(-0.3 * t) - 0.0008 * t
    src = _curve_from_zero(zero_fn, tenors)
    pars = np.array([par_ois_rate(src, int(T)) for T in tenors])

    booted = bootstrap_ois(tenors, pars)
    repriced = np.array([par_ois_rate(booted, int(T)) for T in tenors])
    np.testing.assert_allclose(repriced, pars, atol=1e-12)


def test_bootstrap_roundtrips_arbitrary_discount_factors():
    tenors = np.arange(1, 16)
    zero_fn = lambda t: 0.042 + 0.003 * np.sin(0.5 * t)
    src = _curve_from_zero(zero_fn, tenors)
    pars = np.array([par_ois_rate(src, int(T)) for T in tenors])

    booted = bootstrap_ois(tenors, pars)
    np.testing.assert_allclose(booted.df(tenors), src.df(tenors), atol=1e-12)


def test_par_rate_single_period_identity():
    # For a 1y swap, p_1 = (1 - D_1) / D_1  <=>  D_1 = 1/(1+p_1).
    curve = DiscountCurve([1.0], [1 / 1.05])
    assert par_ois_rate(curve, 1) == pytest.approx(0.05, abs=1e-13)
