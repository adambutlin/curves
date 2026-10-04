"""Set identification of daily structural shocks by sign restrictions.

Shocks follow Cieslak and Pang (2021, Section 2.2), as operationalised in the
pre-registration (Section 3). With variables ordered ``(dy2, dy5, dy10, req)``
and ``b_n`` the impact on the n-year yield:

=================  =======================  ========
shock              yields                   equity
=================  =======================  ========
growth news        all up, b10 < b2, b5     up
monetary (tight)   all up, b2 > b5 > b10    down
common premium     all up, b2 < b5 < b10    down
hedging premium    all down, |b2|<|b5|<|b10|  down
=================  =======================  ========

Short-rate-expectations shocks fade with maturity; risk-premium shocks build
with it. The four sets are mutually exclusive up to sign, so a column of the
impact matrix can satisfy at most one shock's restrictions: matching columns
to shocks is unique and the accepted draws are uniform over the identified set
(Arias, Rubio-Ramírez and Waggoner, 2018, Algorithm 1, sign restrictions only).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

VARIABLES = ("dy2", "dy5", "dy10", "req")
SHOCKS = ("growth", "monetary", "common_premium", "hedging_premium")
EXPECTATIONS_SHOCKS = ("growth", "monetary")
PREMIUM_SHOCKS = ("common_premium", "hedging_premium")


def restriction_matrix(cols: np.ndarray) -> np.ndarray:
    """Boolean (..., 4): does each impact column ``[b2, b5, b10, eq]`` satisfy each shock?"""
    b2, b5, b10, eq = (cols[..., i] for i in range(4))
    growth = (b2 > 0) & (b5 > 0) & (b10 > 0) & (eq > 0) & (b10 < b2) & (b10 < b5)
    monetary = (b10 > 0) & (b5 > b10) & (b2 > b5) & (eq < 0)
    common = (b2 > 0) & (b5 > b2) & (b10 > b5) & (eq < 0)
    hedging = (b2 < 0) & (b5 < b2) & (b10 < b5) & (eq < 0)
    return np.stack([growth, monetary, common, hedging], axis=-1)


def haar_rotations(n: int, size: int, rng: np.random.Generator) -> np.ndarray:
    """``size`` draws from the uniform (Haar) distribution on O(n)."""
    z = rng.standard_normal((size, n, n))
    q, r = np.linalg.qr(z)
    d = np.sign(np.diagonal(r, axis1=1, axis2=2))
    d[d == 0] = 1.0
    return q * d[:, None, :]


def match_columns(B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Match columns of candidate impact matrices (R, n, n) to the four shocks.

    Returns ``(ok_index, B_matched)``: the candidates whose columns can be
    assigned one-to-one to the shocks (with sign flips), and those matrices
    with columns reordered as ``SHOCKS`` and signed as positive shocks.
    """
    cols = np.swapaxes(B, 1, 2)                      # (R, column j, variable)
    pos = restriction_matrix(cols)                   # (R, j, shock k)
    neg = restriction_matrix(-cols)
    sat = pos | neg
    ok = (sat.sum(axis=2) == 1).all(axis=1) & (sat.sum(axis=1) == 1).all(axis=1)
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        return idx, np.empty((0,) + B.shape[1:])
    k_of_j = sat[idx].argmax(axis=2)                                     # (m, j)
    sign = np.where(np.take_along_axis(pos[idx], k_of_j[..., None], 2)[..., 0], 1.0, -1.0)
    flipped = B[idx] * sign[:, None, :]
    j_of_k = np.argsort(k_of_j, axis=1)
    return idx, np.take_along_axis(flipped, j_of_k[:, None, :], axis=2)


@dataclass
class IdentifiedSet:
    """Accepted draws: impact matrices with columns ordered as ``SHOCKS``."""

    B: np.ndarray                 # (J, n, K)
    Sigma: np.ndarray             # (J, n, n)
    A: np.ndarray | None          # (J, k, n) VAR coefficients, or None for a fixed Sigma
    candidates: int
    accepted: int                 # accepted before trimming to the requested number

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.candidates

    def variance_shares(self) -> np.ndarray:
        """(J, n, K): share of each variable's innovation variance due to each shock."""
        var = np.diagonal(self.Sigma, axis1=1, axis2=2)
        return self.B ** 2 / var[:, :, None]

    def median_target(self) -> int:
        """Fry-Pagan: the single draw closest to the pointwise median impact."""
        med = np.median(self.B, axis=0)
        sd = self.B.std(axis=0)
        sd[sd == 0] = 1.0
        return int(np.argmin((((self.B - med) / sd) ** 2).sum(axis=(1, 2))))

    def shocks(self, U: np.ndarray, j: int) -> np.ndarray:
        """Structural shocks (T, K) of draw ``j`` from innovations U (T, n)."""
        return np.linalg.solve(self.B[j], U.T).T


def sample_identified_set(draw: Callable[[int, np.random.Generator], tuple],
                          n_accept: int, rng: np.random.Generator, *,
                          reduced_form_batch: int = 200, rotations_per_draw: int = 250,
                          max_candidates: int = 50_000_000) -> IdentifiedSet:
    """Joint accept-reject over reduced-form draws and Haar rotations.

    ``draw(m, rng)`` returns ``(A, Sigma)`` with shapes (m, k, n) and (m, n, n);
    ``A`` may be ``None`` when Sigma is held fixed. Each reduced-form draw gets
    the same number of rotation candidates, so reduced-form draws enter the
    accepted set in proportion to their acceptance probability, as the joint
    posterior conditional on the restrictions requires.
    """
    Bs, Ss, As = [], [], []
    tried = accepted = 0
    while accepted < n_accept:
        if tried >= max_candidates:
            raise RuntimeError(f"only {accepted} of {n_accept} draws accepted "
                               f"after {tried:,} candidates")
        A, Sig = draw(reduced_form_batch, rng)
        m, n = Sig.shape[0], Sig.shape[1]
        L = np.linalg.cholesky(Sig)
        Q = haar_rotations(n, m * rotations_per_draw, rng).reshape(m, rotations_per_draw, n, n)
        cand = (L[:, None] @ Q).reshape(-1, n, n)
        idx, Bm = match_columns(cand)
        src = idx // rotations_per_draw
        Bs.append(Bm)
        Ss.append(Sig[src])
        As.append(None if A is None else A[src])
        tried += cand.shape[0]
        accepted += len(idx)
    B = np.concatenate(Bs)[:n_accept]
    S = np.concatenate(Ss)[:n_accept]
    A = None if As[0] is None else np.concatenate(As)[:n_accept]
    return IdentifiedSet(B=B, Sigma=S, A=A, candidates=tried, accepted=accepted)


def fixed_sigma(Sigma: np.ndarray) -> Callable[[int, np.random.Generator], tuple]:
    """A ``draw`` function holding Sigma fixed (restriction-only benchmark, placebos)."""
    def _draw(m: int, rng: np.random.Generator):
        return None, np.repeat(Sigma[None], m, axis=0)
    return _draw


def without_stock_bond_covariance(Sigma: np.ndarray, n_yields: int = 3) -> np.ndarray:
    """Sigma with the yield-equity covariances set to zero.

    The learned-from-data benchmark (pre-registration, Section 4.3, as amended
    in the deviations log): keep the yield-curve block, which the restrictions
    need to be satisfiable at all, and remove the stock-bond co-movement, which
    is the cross-asset information that separates growth from monetary news and
    the common from the hedging premium.
    """
    out = Sigma.copy()
    out[:n_yields, n_yields:] = 0.0
    out[n_yields:, :n_yields] = 0.0
    return out


def random_rotations(Sigma: np.ndarray, size: int, rng: np.random.Generator) -> np.ndarray:
    """Unrestricted impact matrices chol(Sigma) Q with Q Haar: the placebo set."""
    L = np.linalg.cholesky(Sigma)
    return L[None] @ haar_rotations(Sigma.shape[0], size, rng)
