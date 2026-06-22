"""Tests for day-count and spot<->discount-factor conventions.

Convention is pinned empirically against the BoE's own published forward curve:
continuous compounding, D(t) = exp(-R(t) * t), with R a decimal rate.
"""
import datetime as dt

import numpy as np
import pytest

from giltcurve.conventions import year_fraction, spot_to_df, df_to_spot


def test_year_fraction_act365f():
    # One calendar year (non-leap span) under ACT/365F is 365/365 = 1.0.
    d0 = dt.date(2025, 1, 1)
    d1 = dt.date(2026, 1, 1)
    assert year_fraction(d0, d1) == pytest.approx(365 / 365)


def test_year_fraction_half_year():
    d0 = dt.date(2025, 1, 1)
    d1 = dt.date(2025, 7, 2)  # 182 days
    assert year_fraction(d0, d1) == pytest.approx(182 / 365)


def test_spot_to_df_continuous_compounding():
    # 4% continuously compounded for 2y -> exp(-0.08).
    assert spot_to_df(0.04, 2.0) == pytest.approx(np.exp(-0.08))


def test_spot_df_roundtrip():
    spot, t = 0.0375, 7.3
    assert df_to_spot(spot_to_df(spot, t), t) == pytest.approx(spot)


def test_spot_to_df_vectorised():
    spots = np.array([0.03, 0.04, 0.05])
    ts = np.array([1.0, 2.0, 3.0])
    np.testing.assert_allclose(spot_to_df(spots, ts), np.exp(-spots * ts))
