"""Market-implied Bank Rate path from the SONIA OIS curve (Step 4).

Economic logic
--------------
SONIA tracks Bank Rate within a few basis points, so the *expected average
SONIA* over a future window equals the *expected average Bank Rate* over that
window, up to a small, slow-moving basis. The forward SONIA rate over an
inter-meeting window [m_k, m_{k+1}] is exactly that expected average. Slicing
the OIS curve at MPC effective dates therefore reads the market-implied policy
path straight off the curve -- the same calculation behind Bloomberg's WIRP.

Conventions
-----------
* The *simple* forward ``(D(t_a)/D(t_b) - 1) / (t_b - t_a)`` is used rather than
  the continuous forward: it matches how money-market rates are quoted and is
  the more faithful read of an average overnight rate. Over a ~7-week window the
  two differ by well under a basis point.
* ``bank_rate_minus_sonia_bp`` translates implied SONIA into implied Bank Rate.
  It cancels out of *changes* in the path, so the cumulative-easing figure
  (``cum_change_bp``) is robust to this assumption -- which is why it, not the
  level, is the headline number.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from giltcurve.conventions import year_fraction
from giltcurve.curves.discount import DiscountCurve


def simple_forward(curve: DiscountCurve, t1: float, t2: float) -> float:
    """Simple (money-market) forward rate over [t1, t2] in year fractions."""
    return (curve.df(t1) / curve.df(t2) - 1.0) / (t2 - t1)


def implied_policy_path(
    curve: DiscountCurve,
    meeting_dates: Sequence[dt.date],
    valuation_date: Optional[dt.date] = None,
    *,
    bank_rate_minus_sonia_bp: float = 0.0,
) -> pd.DataFrame:
    """Implied SONIA / Bank Rate path, one row per inter-meeting window.

    Row 0 is the "spot" window from ``valuation_date`` to the next MPC effective
    date (the current setting). Row k>0 spans [m_{k-1}, m_k] and reflects the
    market's expected rate *after* the decision at meeting ``m_{k-1}``.

    Returns a DataFrame with columns: ``meeting`` (the governing MPC date, or
    None for spot), ``window_start``, ``window_end``, ``fwd_sonia``,
    ``implied_bank_rate``, ``step_bp`` (change vs previous window) and
    ``cum_change_bp`` (change vs the spot window).
    """
    valuation_date = valuation_date or curve.valuation_date
    if valuation_date is None:
        raise ValueError("valuation_date required (pass it or set curve.valuation_date)")

    future = sorted(d for d in meeting_dates if d > valuation_date)
    if not future:
        raise ValueError("no MPC meeting dates fall after the valuation date")

    boundaries = [valuation_date] + future
    basis = bank_rate_minus_sonia_bp / 1e4

    rows = []
    for i in range(len(boundaries) - 1):
        a, b = boundaries[i], boundaries[i + 1]
        ta, tb = year_fraction(valuation_date, a), year_fraction(valuation_date, b)
        fwd = simple_forward(curve, ta, tb) if ta > 0 else simple_forward(curve, 1e-8, tb)
        rows.append(
            {
                "meeting": None if i == 0 else future[i - 1],
                "window_start": a,
                "window_end": b,
                "fwd_sonia": fwd,
                "implied_bank_rate": fwd + basis,
            }
        )

    df = pd.DataFrame(rows)
    spot = df["implied_bank_rate"].iloc[0]
    df["step_bp"] = df["implied_bank_rate"].diff().fillna(0.0) * 1e4
    df["cum_change_bp"] = (df["implied_bank_rate"] - spot) * 1e4
    return df


def implied_cut_probability(
    implied_rate: float, reference_rate: float, step: float = 0.0025
) -> float:
    """Fraction of a rate ``step`` priced as a cut relative to ``reference_rate``.

    Positive => easing priced; negative => tightening priced. e.g. an implied
    rate 15bp below the current rate on a 25bp grid returns 0.60.
    """
    return (reference_rate - implied_rate) / step
