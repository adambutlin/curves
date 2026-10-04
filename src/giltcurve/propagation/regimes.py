"""Regime-dependent identification (Phase 2 pre-registration).

The sign of the stock-bond correlation decides which shocks the cross-asset
co-movement can separate: when Treasuries hedge equity risk (yields fall when
stocks fall) flight-to-quality moves dominate; when bonds and stocks fall
together, inflation and discount-rate news do. One impact matrix for both
regimes misallocates shocks within each. Here the regime is measured in real
time from the trailing correlation, each regime gets its own innovation
covariance and its own set-identified impact matrix, and day-t shocks use the
impact matrix of the regime prevailing on day t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from giltcurve.propagation.identification import (
    IdentifiedSet, random_rotations, sample_identified_set,
)
from giltcurve.propagation.predictive import PREMIUM_IDX, impact_on

HEDGE, COMOVE = 1, -1
WINDOW = 250


def regime_indicator(panel: pd.DataFrame, window: int = WINDOW) -> pd.Series:
    """+1 (hedge) if the trailing correlation of 10y changes with equity returns,
    measured over the ``window`` days before t, is positive; -1 otherwise; NaN
    until the window is full. Day t's own data never enter its classification."""
    rho = panel["dy10"].rolling(window).corr(panel["req"]).shift(1)
    out = pd.Series(np.where(rho > 0, HEDGE, COMOVE), index=panel.index, dtype=float)
    out[rho.isna()] = np.nan
    return out


def iw_posterior(S: np.ndarray, dof: float):
    """A ``draw`` function for Sigma ~ IW(S, dof), VAR coefficients held fixed."""
    dist = stats.invwishart(df=dof, scale=S)

    def _draw(m: int, rng: np.random.Generator):
        sig = np.asarray(dist.rvs(size=m, random_state=rng)).reshape(m, *S.shape)
        return None, sig
    return _draw


def regime_identified_sets(U: np.ndarray, regime: np.ndarray, n_draws: int,
                           rng: np.random.Generator, mask: np.ndarray | None = None) -> dict:
    """One identified set per regime from the innovations of days in that regime.

    ``mask`` restricts which days may be used (e.g. training days only).
    """
    use = np.ones(len(U), bool) if mask is None else mask
    sets = {}
    for R in (HEDGE, COMOVE):
        m = use & (regime == R)
        if m.sum() < 50:
            raise ValueError(f"only {m.sum()} days in regime {R}")
        S = U[m].T @ U[m]
        sets[R] = sample_identified_set(iw_posterior(S, float(m.sum())), n_draws, rng)
    return sets


def regime_shocks(U: np.ndarray, regime: np.ndarray, sets: dict, j: int) -> np.ndarray:
    """Structural shocks of draw j, using each day's regime impact matrix (NaN if unknown)."""
    eps = np.full(U.shape, np.nan)
    for R, ident in sets.items():
        m = regime == R
        eps[m] = np.linalg.solve(ident.B[j], U[m].T).T
    return eps


def regime_premium_contribution(U: np.ndarray, regime: np.ndarray, sets: dict, j: int,
                                outcome: str) -> np.ndarray:
    """The premium-shock part of each day's innovation in ``outcome``, regime by regime."""
    out = np.full(len(U), np.nan)
    for R, ident in sets.items():
        m = regime == R
        eps = np.linalg.solve(ident.B[j], U[m].T).T
        b = impact_on(ident.B[j], outcome)
        out[m] = eps[:, PREMIUM_IDX] @ b[PREMIUM_IDX]
    return out


def placebo_contributions(U: np.ndarray, Sigma: np.ndarray, outcome: str, n: int,
                          rng: np.random.Generator) -> list[np.ndarray]:
    """Random rotations of one regime's covariance with random two-shock groupings."""
    B = random_rotations(Sigma, n, rng)
    b = impact_on(B, outcome)
    out = []
    for i in range(n):
        g = list(rng.choice(4, size=2, replace=False))
        eps = np.linalg.solve(B[i], U.T).T
        out.append(eps[:, g] @ b[i][g])
    return out


def pooled_shares(sets: dict) -> dict:
    """Median variance shares (n, K) per regime."""
    return {R: np.median(ident.variance_shares(), axis=0) for R, ident in sets.items()}


__all__ = ["HEDGE", "COMOVE", "WINDOW", "IdentifiedSet", "regime_indicator", "iw_posterior",
           "regime_identified_sets", "regime_shocks", "regime_premium_contribution",
           "placebo_contributions", "pooled_shares"]
