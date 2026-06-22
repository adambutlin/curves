"""Discount curve with log-linear interpolation in the discount factor.

Log-linear interpolation of ``D(t)`` is equivalent to a **piecewise-constant
instantaneous forward** between nodes, which is the market-standard interpolation
for overnight-index (OIS) curves: it keeps implied forward rates flat between
liquid pillars rather than introducing spurious oscillation. Everything desks
read off the curve -- zero rates, period forwards, the implied policy path -- is
a deterministic transform of this single object.
"""
from __future__ import annotations

import numpy as np


class DiscountCurve:
    """A discount function D(t) defined by pillars, log-linear in log(D).

    Parameters
    ----------
    times : array-like
        Strictly positive maturities in year fractions (ACT/365F).
    dfs : array-like
        Discount factors at ``times``. ``D(0)=1`` is added automatically.
    valuation_date : datetime.date, optional
        Anchor date; enables date-based forward queries downstream.
    """

    def __init__(self, times, dfs, *, valuation_date=None):
        times = np.asarray(times, float)
        dfs = np.asarray(dfs, float)
        if times.ndim != 1 or times.shape != dfs.shape:
            raise ValueError("times and dfs must be 1-D arrays of equal length")
        if np.any(times <= 0):
            raise ValueError("pillar times must be strictly positive")
        order = np.argsort(times)
        # Prepend the t=0, D=1 anchor so interpolation is well defined near zero.
        self.t = np.concatenate([[0.0], times[order]])
        self.logdf = np.concatenate([[0.0], np.log(dfs[order])])
        self.valuation_date = valuation_date

    # -- internal -----------------------------------------------------------
    def _logdf_arr(self, t_arr):
        """log D(t) for a 1-D array, with flat-forward right extrapolation."""
        return _interp_extrap(t_arr, self.t, self.logdf)

    # -- core (scalar in -> scalar out, array in -> array out) --------------
    def log_df(self, t):
        return _scalarize(t, lambda a: self._logdf_arr(a))

    def df(self, t):
        """Discount factor D(t)."""
        return _scalarize(t, lambda a: np.exp(self._logdf_arr(a)))

    def zero(self, t):
        """Continuously-compounded zero (spot) rate, decimal."""
        return _scalarize(t, lambda a: -self._logdf_arr(a) / a)

    def forward(self, t1, t2):
        """Continuously-compounded forward rate over [t1, t2], decimal.

        f(t1,t2) = ln(D(t1)/D(t2)) / (t2 - t1).
        """
        t1a = np.asarray(t1, float)
        t2a = np.asarray(t2, float)
        f = (self._logdf_arr(np.atleast_1d(t1a)) - self._logdf_arr(np.atleast_1d(t2a))) / (
            np.atleast_1d(t2a) - np.atleast_1d(t1a)
        )
        return float(f[0]) if (t1a.ndim == 0 and t2a.ndim == 0) else f

    def inst_forward(self, t, h=1e-5):
        """Instantaneous forward rate f(t) via symmetric finite difference."""

        def _f(a):
            lo = np.maximum(a - h, 0.0)
            return -(self._logdf_arr(a + h) - self._logdf_arr(lo)) / (a + h - lo)

        return _scalarize(t, _f)


def _scalarize(t, fn):
    """Apply ``fn`` (array -> array) but return a Python float for scalar input."""
    t_arr = np.asarray(t, float)
    out = fn(np.atleast_1d(t_arr))
    return float(out[0]) if t_arr.ndim == 0 else out


def _interp_extrap(x, xp, fp):
    """Linear interpolation with linear (flat-forward) right extrapolation."""
    x = np.atleast_1d(np.asarray(x, float))
    y = np.interp(x, xp, fp)
    beyond = x > xp[-1]
    if np.any(beyond):
        slope = (fp[-1] - fp[-2]) / (xp[-1] - xp[-2])
        y = np.where(beyond, fp[-1] + slope * (x - xp[-1]), y)
    return y
