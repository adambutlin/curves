"""Tests for the market-implied Bank Rate path (Step 4).

The forward SONIA rate averaged over an inter-meeting window is the market's
expectation of the average overnight rate while that policy setting is in force.
Slicing the OIS curve at MPC effective dates therefore yields the implied policy
path. Bank Rate is recovered by adding the (small) Bank Rate - SONIA basis.
"""
import datetime as dt

import numpy as np
import pytest

from giltcurve.conventions import year_fraction
from giltcurve.curves.discount import DiscountCurve
from giltcurve.policy.meeting_dated import (
    implied_policy_path,
    implied_cut_probability,
)

VAL = dt.date(2026, 6, 22)
MEETINGS = [dt.date(2026, 8, 6), dt.date(2026, 9, 17), dt.date(2026, 11, 5)]


def _curve_with_window_forwards(window_rates):
    """Build a curve whose simple forward over each inter-meeting window is known."""
    boundaries = [VAL] + MEETINGS
    times, dfs, d_prev = [], [], 1.0
    for i, r in enumerate(window_rates):
        ta = year_fraction(VAL, boundaries[i])
        tb = year_fraction(VAL, boundaries[i + 1])
        d_prev = d_prev / (1.0 + r * (tb - ta))  # simple-forward accrual
        times.append(tb)
        dfs.append(d_prev)
    return DiscountCurve(times, dfs, valuation_date=VAL)


def test_recovers_known_window_forwards():
    rates = [0.0420, 0.0395, 0.0370]  # current, post-Aug, post-Sep
    curve = _curve_with_window_forwards(rates)
    path = implied_policy_path(curve, MEETINGS, VAL)
    np.testing.assert_allclose(path["fwd_sonia"].to_numpy(), rates, atol=1e-12)


def test_first_window_is_spot_and_past_meetings_dropped():
    rates = [0.0420, 0.0395, 0.0370]
    curve = _curve_with_window_forwards(rates)
    past = dt.date(2026, 5, 8)
    path = implied_policy_path(curve, [past] + MEETINGS, VAL)
    assert path.iloc[0]["window_start"] == VAL          # starts today, not in the past
    assert path.iloc[0]["meeting"] is None              # spot/current period
    assert path.iloc[1]["meeting"] == MEETINGS[0]


def test_bank_rate_applies_sonia_basis():
    rates = [0.0420, 0.0395, 0.0370]
    curve = _curve_with_window_forwards(rates)
    basis = 5.0  # Bank Rate sits 5bp above SONIA
    path = implied_policy_path(curve, MEETINGS, VAL, bank_rate_minus_sonia_bp=basis)
    np.testing.assert_allclose(
        path["implied_bank_rate"].to_numpy(),
        np.array(rates) + basis / 1e4,
        atol=1e-12,
    )


def test_cumulative_change_is_basis_invariant():
    rates = [0.0420, 0.0395, 0.0370]
    curve = _curve_with_window_forwards(rates)
    p0 = implied_policy_path(curve, MEETINGS, VAL, bank_rate_minus_sonia_bp=0.0)
    p5 = implied_policy_path(curve, MEETINGS, VAL, bank_rate_minus_sonia_bp=5.0)
    np.testing.assert_allclose(
        p0["cum_change_bp"].to_numpy(), p5["cum_change_bp"].to_numpy(), atol=1e-9
    )
    # Two 25bp cuts priced from the front by the third window.
    assert p0["cum_change_bp"].iloc[-1] == pytest.approx(-50.0, abs=1.0)


def test_implied_cut_probability():
    # 15bp of easing priced against a 25bp grid = 60% chance of a cut.
    assert implied_cut_probability(0.0485, 0.0500, step=0.0025) == pytest.approx(0.60)
    # A hike shows as a negative "cut" probability.
    assert implied_cut_probability(0.0515, 0.0500, step=0.0025) == pytest.approx(-0.60)
