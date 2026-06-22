"""Bank of England MPC meeting-date calendar.

The implied-policy-path slicing only needs the dates on which Bank Rate can
change. Rate decisions are announced on the meeting date and take effect the
following business day; that one-day shift is immaterial to the path shape, so
we slice on announcement dates.

NOTE ON PROVENANCE
------------------
2024-2025 are the BoE's published/realised announcement dates. 2026-2027 follow
the BoE's regular ~6-weekly cadence and should be reconciled against the
official calendar before any production use:
https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
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
    # 2026 (projected from BoE cadence -- verify)
    D(2026, 2, 5), D(2026, 3, 19), D(2026, 5, 7), D(2026, 6, 18),
    D(2026, 8, 6), D(2026, 9, 17), D(2026, 11, 5), D(2026, 12, 17),
    # 2027 (projected -- verify)
    D(2027, 2, 4), D(2027, 3, 18), D(2027, 5, 6), D(2027, 6, 17),
    D(2027, 8, 5), D(2027, 9, 16), D(2027, 11, 4), D(2027, 12, 16),
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
