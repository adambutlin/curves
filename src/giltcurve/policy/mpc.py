"""Bank of England MPC meeting-date calendar.

The implied-policy-path slicing only needs the dates on which Bank Rate can
change. Rate decisions are announced on the meeting date -- always a Thursday
-- and take effect the following business day; that one-day shift is
immaterial to the path shape, so we slice on announcement dates.

NOTE ON PROVENANCE
------------------
2024-2025 are the BoE's published/realised announcement dates. 2026-2027 were
originally projected from the BoE's ~6-weekly meeting cadence, and that
projection was wrong: the real cadence is irregular around the months carrying
a Monetary Policy Report, so simple arithmetic drifted the Apr/Aug/May-ish
meetings by about a week. On 2026-08-20 the 2026-2027 entries were reconciled
against the published calendar:
https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
(page last updated 26 May 2026 -- the page rolls forward to show later years,
so a newer read of it may show different or additional dates than this one).
2026 is confirmed; 2027 is provisional -- the BoE itself labels it that way,
and it may still move. 2028+ is not yet on the calendar and will need the same
reconciliation once published; do not re-derive it from the ~6-weekly cadence.
This list is deliberately a plain constant so it is trivial to update.
"""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

D = dt.date

MPC_ANNOUNCEMENT_DATES: List[dt.date] = [
    # 2024 (realised)
    D(2024, 2, 1), D(2024, 3, 21), D(2024, 5, 9), D(2024, 6, 20),
    D(2024, 8, 1), D(2024, 9, 19), D(2024, 11, 7), D(2024, 12, 19),
    # 2025 (scheduled/realised)
    D(2025, 2, 6), D(2025, 3, 20), D(2025, 5, 8), D(2025, 6, 19),
    D(2025, 8, 7), D(2025, 9, 18), D(2025, 11, 6), D(2025, 12, 18),
    # 2026 (published BoE calendar, reconciled 2026-08-20 -- no longer projected)
    D(2026, 2, 5), D(2026, 3, 19), D(2026, 4, 30), D(2026, 6, 18),
    D(2026, 7, 30), D(2026, 9, 17), D(2026, 11, 5), D(2026, 12, 17),
    # 2027 (published BoE calendar, provisional -- reconciled 2026-08-20)
    D(2027, 2, 4), D(2027, 3, 18), D(2027, 4, 29), D(2027, 6, 17),
    D(2027, 7, 29), D(2027, 9, 16), D(2027, 11, 4), D(2027, 12, 16),
]


def upcoming_mpc_dates(
    valuation_date: dt.date, n: Optional[int] = None
) -> List[dt.date]:
    """MPC announcement dates strictly after ``valuation_date`` (optionally first ``n``)."""
    future = sorted(d for d in MPC_ANNOUNCEMENT_DATES if d > valuation_date)
    return future[:n] if n is not None else future


def effective_dates(announcement_dates: List[dt.date]) -> List[dt.date]:
    """Bank Rate effective dates: the business day after each announcement."""
    out = []
    for d in announcement_dates:
        nxt = d + dt.timedelta(days=1)
        while nxt.weekday() >= 5:  # skip Sat/Sun
            nxt += dt.timedelta(days=1)
        out.append(nxt)
    return out
