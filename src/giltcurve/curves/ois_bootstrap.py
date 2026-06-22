"""SONIA OIS discount-curve bootstrap (Step 2).

This is the from-scratch engine: given par overnight-index-swap (OIS) quotes on
an integer-year grid it strips the discount factors sequentially, with no
external pricing library. The two market facts that make it simple and exact:

1.  On the collateral-discount (= SONIA) curve the compounded-SONIA floating leg
    of an OIS prices to ``PV_float = 1 - D(T)`` (the daily-compounding telescopes,
    ignoring the small payment-lag convexity).
2.  The fixed leg pays an annual coupon ``p`` on ACT/365F, so its PV is
    ``p * sum_i tau_i D(t_i)``.

Equating the two and solving for the newest pillar gives, with annuity
``A_{N-1} = sum_{i<N} tau_i D(t_i)`` already known,

    D(t_N) = (1 - p_N * A_{N-1}) / (1 + p_N * tau_N).

For a desk that prices off Bloomberg/ICVS par quotes, replace ``par_ois_rate``'s
inputs with the quoted swap rates; the bootstrap is unchanged. A ``rateslib``
cross-check lives under the ``[validate]`` extra.
"""
from __future__ import annotations

import numpy as np

from .discount import DiscountCurve


def _annual_schedule(tenor_years: int):
    """Annual payment times and ACT/365F accruals for an integer-year swap."""
    n = int(tenor_years)
    if n < 1 or n != tenor_years:
        raise ValueError("tenor_years must be a positive integer on the annual grid")
    times = np.arange(1, n + 1, dtype=float)
    accruals = np.ones(n)  # 1y on ACT/365F ~ 1.0
    return times, accruals


def par_ois_rate(curve: DiscountCurve, tenor_years: int) -> float:
    """Par (fair) fixed rate of an annual SONIA OIS to ``tenor_years``."""
    times, accruals = _annual_schedule(tenor_years)
    dfs = curve.df(times)
    annuity = float(np.sum(accruals * dfs))
    return (1.0 - float(dfs[-1])) / annuity


def bootstrap_ois(tenors, par_rates, *, valuation_date=None) -> DiscountCurve:
    """Bootstrap discount factors from par OIS quotes on a consecutive annual grid.

    Parameters
    ----------
    tenors : array-like of int
        Consecutive integer-year maturities ``[1, 2, ..., N]``.
    par_rates : array-like of float
        Par swap rates (decimal) at ``tenors``.
    valuation_date : datetime.date, optional
        Passed through to the resulting :class:`DiscountCurve`.

    Returns
    -------
    DiscountCurve
        Discount factors at the input tenors (log-linear in between).
    """
    tenors = np.asarray(tenors)
    par_rates = np.asarray(par_rates, float)
    if tenors.shape != par_rates.shape:
        raise ValueError("tenors and par_rates must have matching shape")
    if not np.array_equal(tenors, np.arange(1, tenors.size + 1)):
        raise ValueError(
            "bootstrap_ois expects a consecutive annual grid [1..N]; "
            "gap-tenor curves need intermediate interpolation (roadmap)."
        )

    dfs = np.empty(tenors.size)
    annuity = 0.0  # running sum_i tau_i D(t_i), tau = 1 annual
    for k, p in enumerate(par_rates):
        tau = 1.0
        dfs[k] = (1.0 - p * annuity) / (1.0 + p * tau)
        annuity += tau * dfs[k]
    return DiscountCurve(tenors.astype(float), dfs, valuation_date=valuation_date)
