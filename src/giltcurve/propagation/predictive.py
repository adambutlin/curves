"""Propagation tests: does the origin of a yield move predict what follows?

Outcomes are subsequent changes ``r_{t,t+h} = x_{t+h} - x_t`` (basis points)
for the 10-year yield, the 2-year yield and the 2s10s slope; the day-t move is
excluded. Three tests, pre-registered in Section 5:

A. Reduced-form content. Do the other innovations of day t predict r given the
   own move and the curve state? This is the proposal's null, and its answer
   is the same under every identification (rotation invariance).
B. Propagation ratios. ``pi_k = gamma_k / b_k``: the fraction of the day-t move
   caused by shock k that continues (> 0) or reverses (< 0).
C. A two-dimensional structural state. Does the premium-shock part of today's
   move propagate differently from the expectations-shock part, beyond what a
   random split of the same innovation achieves?
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from giltcurve.propagation.identification import PREMIUM_SHOCKS, SHOCKS

HORIZONS = (1, 5, 10, 20)
OUTCOMES = ("y10", "y2", "slope")
# Row of the impact matrix (variables dy2, dy5, dy10, req) for each outcome.
_OUTCOME_ROWS = {"y10": (2, None), "y2": (0, None), "slope": (2, 0)}
# Three innovations that, with the own move, span all four.
_OTHER_INNOVATIONS = {"y10": [0, 1, 3], "y2": [1, 2, 3], "slope": [0, 1, 3]}
PREMIUM_IDX = [SHOCKS.index(s) for s in PREMIUM_SHOCKS]


# ---------------------------------------------------------------- data objects
def outcome_levels(panel: pd.DataFrame) -> pd.DataFrame:
    """Levels in basis points: 10-year, 2-year and the 2s10s slope."""
    return pd.DataFrame({"y10": panel["y10"] * 100.0, "y2": panel["y2"] * 100.0,
                         "slope": (panel["y10"] - panel["y2"]) * 100.0}, index=panel.index)


def own_moves(panel: pd.DataFrame) -> pd.DataFrame:
    """The observed day-t change of each outcome (basis points)."""
    return pd.DataFrame({"y10": panel["dy10"], "y2": panel["dy2"],
                         "slope": panel["dy10"] - panel["dy2"]}, index=panel.index)


def forward_changes(panel: pd.DataFrame, horizons=HORIZONS) -> dict:
    """``{(outcome, h): r_{t,t+h}}``, NaN where t+h lies beyond the sample."""
    lv = outcome_levels(panel)
    return {(o, h): lv[o].shift(-h) - lv[o] for o in OUTCOMES for h in horizons}


def curve_controls(panel: pd.DataFrame) -> pd.DataFrame:
    """Z_t, all known at the close of day t (pre-registration, Section 5)."""
    y10 = panel["y10"] * 100.0
    return pd.DataFrame({
        "level": panel["y10"],
        "slope": (panel["y10"] - panel["y2"]) * 100.0,
        "mom20": y10.shift(1) - y10.shift(21),
        "vol20": panel["dy10"].shift(1).rolling(20).std(),
    }, index=panel.index)


def impact_on(B: np.ndarray, outcome: str) -> np.ndarray:
    """Impact of each shock on the outcome, for one draw (n, K) or many (J, n, K)."""
    i, j = _OUTCOME_ROWS[outcome]
    row = B[..., i, :]
    return row if j is None else row - B[..., j, :]


def innovation_of(U: np.ndarray, outcome: str) -> np.ndarray:
    i, j = _OUTCOME_ROWS[outcome]
    return U[:, i] if j is None else U[:, i] - U[:, j]


# ---------------------------------------------------------------- regression
def ols_nw(y: np.ndarray, X: np.ndarray, lags: int):
    """OLS with a Newey-West (Bartlett) covariance. Returns (beta, V, r2)."""
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    g = X * e[:, None]
    S = g.T @ g
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        G = g[l:].T @ g[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    r2 = 1.0 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return beta, V, float(r2)


def r2_only(y: np.ndarray, X: np.ndarray) -> float:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    return float(1.0 - (e @ e) / ((y - y.mean()) @ (y - y.mean())))


def wald(beta: np.ndarray, V: np.ndarray, R: np.ndarray) -> tuple[float, float]:
    """Wald statistic and chi-square p-value for H0: R beta = 0."""
    Rb = R @ beta
    W = float(Rb @ np.linalg.solve(R @ V @ R.T, Rb))
    return W, float(stats.chi2.sf(W, R.shape[0]))


def _stack(*cols) -> np.ndarray:
    return np.column_stack([np.ones(len(cols[0]))] + [np.asarray(c, float) for c in cols])


def _valid(r: np.ndarray, *blocks) -> np.ndarray:
    m = np.isfinite(r)
    for b in blocks:
        b = np.asarray(b, float)
        m &= np.isfinite(b).all(axis=1) if b.ndim == 2 else np.isfinite(b)
    return m


# ---------------------------------------------------------------- Test A
def reduced_form_test(r, own, U, Z, outcome: str, h: int) -> dict:
    """Do the other day-t innovations predict r given the own move and Z?"""
    others = U[:, _OTHER_INNOVATIONS[outcome]]
    m = _valid(r, own, others, Z)
    X0 = _stack(own[m], Z[m])
    X1 = _stack(own[m], Z[m], others[m])
    beta, V, r2_1 = ols_nw(r[m], X1, h)
    q = others.shape[1]
    R = np.zeros((q, X1.shape[1]))
    R[:, -q:] = np.eye(q)
    W, p = wald(beta, V, R)
    return {"outcome": outcome, "h": h, "n": int(m.sum()), "wald": W, "p": p,
            "own_coef": float(beta[1]), "own_se": float(np.sqrt(V[1, 1])),
            "r2_restricted": r2_only(r[m], X0), "r2_full": r2_1,
            "incr_r2": r2_1 - r2_only(r[m], X0)}


# ---------------------------------------------------------------- Test B
def propagation_ratio_test(r, eps, b, Z, h: int) -> dict:
    """Propagation ratios for one draw: r on all shocks and Z."""
    m = _valid(r, eps, Z)
    X = _stack(eps[m], Z[m])
    beta, V, _ = ols_nw(r[m], X, h)
    K = eps.shape[1]
    gamma = beta[1:1 + K]
    se = np.sqrt(np.diag(V)[1:1 + K])
    R = np.zeros((K - 1, X.shape[1]))          # H0: gamma_k / b_k equal for all k
    for i in range(1, K):
        R[i - 1, 1] = -1.0 / b[0]
        R[i - 1, 1 + i] = 1.0 / b[i]
    W, p = wald(beta, V, R)
    return {"gamma": gamma, "gamma_se": se, "pi": gamma / b, "wald_equal_pi": W, "p_equal_pi": p}


# ---------------------------------------------------------------- Test C
def premium_contribution(eps: np.ndarray, b: np.ndarray, group=PREMIUM_IDX) -> np.ndarray:
    """The part of the outcome's day-t innovation due to the shocks in ``group``."""
    return eps[:, group] @ b[group]


def structural_split_test(r, own, contrib, Z, h: int, *, with_se: bool = True) -> dict:
    """r on own move, the premium-shock contribution and Z; kappa = theta_TP - theta_EH."""
    m = _valid(r, own, contrib, Z)
    X0 = _stack(own[m], Z[m])
    X1 = _stack(own[m], contrib[m], Z[m])
    r2_0 = r2_only(r[m], X0)
    if with_se:
        beta, V, r2_1 = ols_nw(r[m], X1, h)
        t = float(beta[2] / np.sqrt(V[2, 2]))
    else:
        r2_1, beta, t = r2_only(r[m], X1), np.linalg.lstsq(X1, r[m], rcond=None)[0], np.nan
    return {"theta_eh": float(beta[1]), "theta_tp": float(beta[1] + beta[2]),
            "kappa": float(beta[2]), "t_kappa": t, "incr_r2": r2_1 - r2_0}


# ---------------------------------------------------------------- Phase 3: size of news
EXPECTATIONS_IDX = [SHOCKS.index(s) for s in ("growth", "monetary")]


def large_part(c: np.ndarray, sd: float, k: float = 2.0) -> np.ndarray:
    """The component on days when it exceeds ``k`` standard deviations, zero otherwise."""
    return np.where(np.abs(c) > k * sd, c, 0.0)


def size_split_test(r, own, c_tp, big_eh, big_tp, Z, h: int, *, with_se: bool = True) -> dict:
    """Phase 3: extra propagation of large expectations and large premium news.

    r = a + b*own + kappa*C_TP + lam_EH*C_EH*L_EH + lam_TP*C_TP*L_TP + d'Z; the
    incremental R^2 is measured against the MVP split model (without the size terms).
    """
    m = _valid(r, own, c_tp, big_eh, big_tp, Z)
    X0 = _stack(own[m], c_tp[m], Z[m])
    X1 = _stack(own[m], c_tp[m], big_eh[m], big_tp[m], Z[m])
    r2_0 = r2_only(r[m], X0)
    if with_se:
        beta, V, r2_1 = ols_nw(r[m], X1, h)
        se = np.sqrt(np.diag(V))
        t_eh, t_tp = float(beta[3] / se[3]), float(beta[4] / se[4])
    else:
        beta = np.linalg.lstsq(X1, r[m], rcond=None)[0]
        r2_1, t_eh, t_tp = r2_only(r[m], X1), np.nan, np.nan
    return {"lambda_eh": float(beta[3]), "lambda_tp": float(beta[4]), "t_eh": t_eh,
            "t_tp": t_tp, "incr_r2": r2_1 - r2_0,
            "large_eh_days": int((big_eh[m] != 0).sum()), "large_tp_days": int((big_tp[m] != 0).sum())}
