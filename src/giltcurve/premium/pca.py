"""Principal-component pricing factors for a zero-coupon yield panel.

The ACM model uses the first ``K`` principal components of the yield panel as
observable pricing factors. The leading three are the classic level / slope /
curvature. PCA is computed from scratch via the SVD of the demeaned panel:
loadings are the right singular vectors, factor scores are the projections of the
demeaned yields onto them, and the explained-variance ratios come from the
squared singular values. This module is currency-agnostic — it sees only numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PCAResult:
    """Fitted PCA of a yield panel.

    Attributes
    ----------
    mean : (N,) per-maturity sample mean (the panel is demeaned before PCA).
    loadings : (N, K) orthonormal columns; column j is PC j's loading vector.
    factors : (T, K) factor scores (demeaned yields projected onto loadings).
    explained_var : (K,) fraction of total panel variance per component.
    maturities : (N,) maturity grid (years) the loadings are defined on.
    """

    mean: np.ndarray
    loadings: np.ndarray
    factors: np.ndarray
    explained_var: np.ndarray
    maturities: np.ndarray

    def project(self, yields) -> np.ndarray:
        """Map (annualised) yields onto the fitted loadings -> factor scores.

        Lets parameters estimated on a monthly panel be evaluated on any later
        (e.g. daily) yields. Accepts a 1-D row or a 2-D (rows x maturities) array.
        """
        y = np.atleast_2d(np.asarray(yields, float))
        out = (y - self.mean) @ self.loadings
        return out[0] if np.ndim(yields) == 1 else out


def yield_pca(panel: pd.DataFrame, k: int = 5) -> PCAResult:
    """Extract the first ``k`` principal components of a yield panel.

    Parameters
    ----------
    panel : DataFrame, index=date, columns=maturity(years), values=yield(decimal).
    k : number of components to retain.
    """
    Y = panel.to_numpy(float)
    if Y.shape[0] <= k:
        raise ValueError("need more observations than components")
    mean = Y.mean(axis=0)
    Yc = Y - mean
    _, S, Vt = np.linalg.svd(Yc, full_matrices=False)
    loadings = Vt[:k].T.copy()
    factors = Yc @ loadings
    explained_var = (S[:k] ** 2) / (S ** 2).sum()
    # Sign convention: each component points so its loadings sum positive
    # (PC1 => a parallel "level" rise raises the factor).
    for j in range(k):
        if loadings[:, j].sum() < 0:
            loadings[:, j] *= -1.0
            factors[:, j] *= -1.0
    return PCAResult(mean, loadings, factors, explained_var, panel.columns.to_numpy(float))
