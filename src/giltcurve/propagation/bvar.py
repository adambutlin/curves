"""Bayesian VAR with a conjugate normal-inverse-Wishart (Minnesota) prior.

The prior is implemented with dummy observations (Bańbura, Giannone and
Reichlin, 2010), which makes the posterior exact and cheap:

    Y* = [Y_d; Y],  X* = [X_d; X],
    A_hat = (X*'X*)^{-1} X*'Y*,  S = (Y* - X* A_hat)'(Y* - X* A_hat),
    Sigma | Y ~ IW(S, T* - k + 2),
    vec(A) | Sigma, Y ~ N(vec(A_hat), Sigma (x) (X*'X*)^{-1}).

Every variable in the structural-propagation system is already a change or a
return, so the prior mean of every lag coefficient is zero. ``lam`` is the
overall tightness (smaller = more shrinkage); lag ``l`` is shrunk by a further
factor ``l``. The constant is left essentially unrestricted.

Design-matrix column order: ``[const, lag-1 block (n), lag-2 block (n), ...]``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


def design(Y: np.ndarray, p: int) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(Y_t, X_t)`` for t = p..T-1 with X_t = [1, Y_{t-1}, ..., Y_{t-p}]."""
    Y = np.asarray(Y, float)
    T = Y.shape[0]
    lags = [Y[p - l:T - l] for l in range(1, p + 1)]
    X = np.column_stack([np.ones(T - p)] + lags)
    return Y[p:], X


def _ar_residual_sd(y: np.ndarray, p: int) -> float:
    yy, xx = design(y[:, None], p)
    coef, *_ = np.linalg.lstsq(xx, yy, rcond=None)
    resid = yy - xx @ coef
    return float(resid.std(ddof=xx.shape[1]))


def minnesota_dummies(sd: np.ndarray, p: int, lam: float, const_precision: float = 1e-4):
    """Dummy observations for a zero-mean Minnesota prior with lag decay ``l``."""
    n = len(sd)
    k = 1 + n * p
    rows_y, rows_x = [], []
    for l in range(1, p + 1):                       # lag coefficients, prior mean 0
        xd = np.zeros((n, k))
        xd[:, 1 + (l - 1) * n: 1 + l * n] = np.diag(sd * l / lam)
        rows_x.append(xd)
        rows_y.append(np.zeros((n, n)))
    rows_y.append(np.diag(sd))                      # residual covariance scale
    rows_x.append(np.zeros((n, k)))
    xc = np.zeros((1, k))                           # near-flat prior on the constant
    xc[0, 0] = const_precision
    rows_x.append(xc)
    rows_y.append(np.zeros((1, n)))
    return np.vstack(rows_y), np.vstack(rows_x)


@dataclass
class BVARPosterior:
    p: int
    A_hat: np.ndarray        # (k, n) posterior mean of the coefficients
    XtX_inv: np.ndarray      # (k, k)
    S: np.ndarray            # (n, n) posterior scale of Sigma
    dof: float
    Y: np.ndarray            # (T, n) data rows used in estimation
    X: np.ndarray            # (T, k)

    @property
    def n(self) -> int:
        return self.S.shape[0]

    @property
    def sigma_mean(self) -> np.ndarray:
        return self.S / (self.dof - self.n - 1)

    def residuals(self, A: np.ndarray | None = None, Y=None, X=None) -> np.ndarray:
        A = self.A_hat if A is None else A
        Y = self.Y if Y is None else Y
        X = self.X if X is None else X
        return Y - X @ A

    def draw(self, ndraw: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
        """Exact posterior draws ``(A, Sigma)`` with shapes (ndraw, k, n), (ndraw, n, n)."""
        sig = stats.invwishart(df=self.dof, scale=self.S).rvs(size=ndraw, random_state=rng)
        sig = np.asarray(sig).reshape(ndraw, self.n, self.n)
        lx = np.linalg.cholesky(self.XtX_inv)
        z = rng.standard_normal((ndraw,) + self.A_hat.shape)
        ls = np.linalg.cholesky(sig)
        A = self.A_hat[None] + lx[None] @ z @ np.swapaxes(ls, 1, 2)
        return A, sig


def fit_bvar(Y: np.ndarray, p: int = 1, lam: float = 0.2) -> BVARPosterior:
    """Posterior of a VAR(p) with constant under the zero-mean Minnesota prior."""
    Y = np.asarray(Y, float)
    n = Y.shape[1]
    sd = np.array([_ar_residual_sd(Y[:, i], p) for i in range(n)])
    Yd, Xd = minnesota_dummies(sd, p, lam)
    Yt, Xt = design(Y, p)
    Ys, Xs = np.vstack([Yd, Yt]), np.vstack([Xd, Xt])
    XtX_inv = np.linalg.inv(Xs.T @ Xs)
    A_hat = XtX_inv @ Xs.T @ Ys
    E = Ys - Xs @ A_hat
    S = E.T @ E
    dof = Ys.shape[0] - Xs.shape[1] + 2
    return BVARPosterior(p=p, A_hat=A_hat, XtX_inv=XtX_inv, S=S, dof=float(dof), Y=Yt, X=Xt)


def impulse_responses(A: np.ndarray, p: int, horizon: int) -> np.ndarray:
    """Reduced-form moving-average weights Psi_0..Psi_horizon, shape (horizon+1, n, n).

    With Y_t = c + sum_l Phi_l Y_{t-l} + u_t and the design's coefficient layout
    (``A`` is (1 + n p, n), lag-l block in rows 1+(l-1)n .. l n), Phi_l = A_l' and
    Psi_0 = I, Psi_s = sum_{l=1}^{min(s,p)} Phi_l Psi_{s-l}. Structural responses to
    shock k are Psi_s B[:, k].
    """
    n = A.shape[1]
    Phi = [A[1 + (l - 1) * n: 1 + l * n].T for l in range(1, p + 1)]
    Psi = np.zeros((horizon + 1, n, n))
    Psi[0] = np.eye(n)
    for s in range(1, horizon + 1):
        for l in range(1, min(s, p) + 1):
            Psi[s] += Phi[l - 1] @ Psi[s - l]
    return Psi


def historical_contributions(eps: np.ndarray, Theta: np.ndarray) -> np.ndarray:
    """Contribution of each shock to each variable, day by day, through the dynamics.

    ``eps`` (T, K) are structural shocks and ``Theta`` (S+1, n, K) the structural
    responses Psi_s B. Returns (T, n, K): sum over s <= S of Theta_s[:, k] eps_{t-s, k}.
    """
    T, K = eps.shape
    S = Theta.shape[0] - 1
    out = np.zeros((T, Theta.shape[1], K))
    for s in range(S + 1):
        out[s:] += eps[: T - s, None, :] * Theta[s][None, :, :]
    return out
