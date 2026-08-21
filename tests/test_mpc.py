"""Tests for the MPC meeting-date calendar helper."""
import datetime as dt

from giltcurve.policy.mpc import upcoming_mpc_dates, MPC_ANNOUNCEMENT_DATES


def test_dates_are_sorted_and_unique():
    assert MPC_ANNOUNCEMENT_DATES == sorted(MPC_ANNOUNCEMENT_DATES)
    assert len(set(MPC_ANNOUNCEMENT_DATES)) == len(MPC_ANNOUNCEMENT_DATES)
    assert all(d.weekday() == 3 for d in MPC_ANNOUNCEMENT_DATES)  # BoE announces on Thursdays


def test_upcoming_returns_only_future_sorted():
    val = dt.date(2026, 6, 22)
    out = upcoming_mpc_dates(val)
    assert all(d > val for d in out)
    assert out == sorted(out)
    assert out[0] == dt.date(2026, 7, 30)  # next scheduled meeting after valuation


def test_upcoming_respects_limit():
    val = dt.date(2026, 6, 22)
    assert len(upcoming_mpc_dates(val, n=3)) == 3


MPC_2026 = (
    dt.date(2026, 2, 5), dt.date(2026, 3, 19), dt.date(2026, 4, 30), dt.date(2026, 6, 18),
    dt.date(2026, 7, 30), dt.date(2026, 9, 17), dt.date(2026, 11, 5), dt.date(2026, 12, 17),
)

MPC_2027 = (
    dt.date(2027, 2, 4), dt.date(2027, 3, 18), dt.date(2027, 4, 29), dt.date(2027, 6, 17),
    dt.date(2027, 7, 29), dt.date(2027, 9, 16), dt.date(2027, 11, 4), dt.date(2027, 12, 16),
)


def test_verified_2026_announcement_dates_are_exactly_these():
    """Confirmed 2026 calendar, retrieved 2026-08-20 from
    https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
    (page last updated 26 May 2026). Asserting the complete set, not just a
    sample, is what catches a one-week drift on any single date -- the same
    error class that produced the original wrong constant.
    """
    assert tuple(d for d in MPC_ANNOUNCEMENT_DATES if d.year == 2026) == MPC_2026


def test_verified_2027_announcement_dates_are_exactly_these():
    """Provisional 2027 calendar (BoE's own label), retrieved 2026-08-20 from
    https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
    (page last updated 26 May 2026).
    """
    assert tuple(d for d in MPC_ANNOUNCEMENT_DATES if d.year == 2027) == MPC_2027


def test_eight_scheduled_meetings_per_year_2024_to_2027():
    for year in (2024, 2025, 2026, 2027):
        n = sum(1 for d in MPC_ANNOUNCEMENT_DATES if d.year == year)
        assert n == 8, f"{year} has {n} announcement dates, expected 8"


def test_consecutive_meetings_are_four_to_ten_weeks_apart():
    for a, b in zip(MPC_ANNOUNCEMENT_DATES, MPC_ANNOUNCEMENT_DATES[1:]):
        gap = (b - a).days
        assert 28 <= gap <= 70, f"implausible gap of {gap} days between {a} and {b}"
