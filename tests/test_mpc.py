"""Tests for the MPC meeting-date calendar helper."""
import datetime as dt

import pytest

from giltcurve.policy.mpc import upcoming_mpc_dates, MPC_ANNOUNCEMENT_DATES


def test_dates_are_sorted_and_unique():
    assert MPC_ANNOUNCEMENT_DATES == sorted(MPC_ANNOUNCEMENT_DATES)
    assert len(set(MPC_ANNOUNCEMENT_DATES)) == len(MPC_ANNOUNCEMENT_DATES)


def test_upcoming_returns_only_future_sorted():
    val = dt.date(2026, 6, 22)
    out = upcoming_mpc_dates(val)
    assert all(d > val for d in out)
    assert out == sorted(out)
    assert out[0] == dt.date(2026, 7, 30)  # next scheduled meeting after valuation


def test_upcoming_respects_limit():
    val = dt.date(2026, 6, 22)
    assert len(upcoming_mpc_dates(val, n=3)) == 3


def test_verified_2026_announcement_dates_are_present():
    """Dates confirmed against the published BoE calendar; see plan Task 2."""
    for d in (dt.date(2026, 3, 19), dt.date(2026, 4, 30), dt.date(2026, 6, 18),
              dt.date(2026, 7, 30), dt.date(2026, 9, 17)):
        assert d in MPC_ANNOUNCEMENT_DATES, f"{d} missing from the MPC calendar"


@pytest.mark.parametrize("stale", [
    dt.date(2026, 5, 7), dt.date(2026, 8, 6),
    dt.date(2027, 5, 6), dt.date(2027, 8, 5),
])
def test_stale_projected_dates_are_gone(stale):
    """The ~6-weekly projection drifted around Monetary Policy Report months.

    Real announcements were 30 Apr / 30 Jul 2026 and 29 Apr / 29 Jul 2027.
    """
    assert stale not in MPC_ANNOUNCEMENT_DATES


def test_verified_2027_announcement_dates_are_present():
    for d in (dt.date(2027, 4, 29), dt.date(2027, 7, 29)):
        assert d in MPC_ANNOUNCEMENT_DATES, f"{d} missing from the MPC calendar"


def test_calendar_is_sorted_unique_and_on_weekdays():
    assert MPC_ANNOUNCEMENT_DATES == sorted(MPC_ANNOUNCEMENT_DATES)
    assert len(set(MPC_ANNOUNCEMENT_DATES)) == len(MPC_ANNOUNCEMENT_DATES)
    assert all(d.weekday() < 5 for d in MPC_ANNOUNCEMENT_DATES)


def test_eight_scheduled_meetings_per_year_2024_to_2027():
    for year in (2024, 2025, 2026, 2027):
        n = sum(1 for d in MPC_ANNOUNCEMENT_DATES if d.year == year)
        assert n == 8, f"{year} has {n} announcement dates, expected 8"


def test_consecutive_meetings_are_four_to_ten_weeks_apart():
    for a, b in zip(MPC_ANNOUNCEMENT_DATES, MPC_ANNOUNCEMENT_DATES[1:]):
        gap = (b - a).days
        assert 28 <= gap <= 70, f"implausible gap of {gap} days between {a} and {b}"
