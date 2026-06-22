"""Day-count and rate/discount-factor conventions for the GBP OIS curve.

All rates in this project are **continuously compounded decimals** unless stated
otherwise. That convention is not arbitrary: it is the one that reproduces the
Bank of England's own published instantaneous-forward curve from its published
spot curve (continuous => 0.3bp RMSE vs annual => 8.5bp; see
``notebooks``/README). Discounting therefore uses ``D(t) = exp(-R(t) * t)``.

SONIA legs accrue on **ACT/365 fixed**, the GBP money-market standard.
"""
from __future__ import annotations

import datetime as dt
from typing import Union

import numpy as np

DAYS_PER_YEAR = 365.0  # ACT/365F

Number = Union[float, np.ndarray]


def year_fraction(start: dt.date, end: dt.date) -> float:
    """ACT/365F year fraction between two dates."""
    return (end - start).days / DAYS_PER_YEAR


def spot_to_df(spot: Number, t: Number) -> Number:
    """Continuously-compounded spot rate (decimal) -> discount factor."""
    return np.exp(-np.asarray(spot, float) * np.asarray(t, float))


def df_to_spot(df: Number, t: Number) -> Number:
    """Discount factor -> continuously-compounded spot rate (decimal)."""
    return -np.log(np.asarray(df, float)) / np.asarray(t, float)
