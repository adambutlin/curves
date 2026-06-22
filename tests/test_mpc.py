"""Tests for the MPC meeting-date calendar helper."""
import datetime as dt

from giltcurve.policy.mpc import upcoming_mpc_dates, MPC_ANNOUNCEMENT_DATES


def test_dates_are_sorted_and_unique():
    assert MPC_ANNOUNCEMENT_DATES == sorted(MPC_ANNOUNCEMENT_DATES)
    assert len(set(MPC_ANNOUNCEMENT_DATES)) == len(MPC_ANNOUNCEMENT_DATES)


def test_upcoming_returns_only_future_sorted():
    val = dt.date(2026, 6, 22)
    out = upcoming_mpc_dates(val)
    assert all(d > val for d in out)
    assert out == sorted(out)
    assert out[0] == dt.date(2026, 8, 6)  # next scheduled meeting after valuation


def test_upcoming_respects_limit():
    val = dt.date(2026, 6, 22)
    assert len(upcoming_mpc_dates(val, n=3)) == 3
