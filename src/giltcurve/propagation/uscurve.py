"""The US Treasury curve through the frozen cross-Atlantic model (pre-registration 15).

The cross-Atlantic model (Brandt et al., 2021; :mod:`giltcurve.propagation.brandt`)
identifies five daily shocks from euro-area and US rates, equities and the euro-dollar
rate. It contains one Treasury yield. Other maturities, and the NY Fed's daily
expectations/term-premium split, are attached by projection on the identified shocks,
which leaves the identification untouched:

    dy_t = c + sum_k sum_{s=0..L} theta_{k,s} eps_{k,t-s} + u_t,

estimated draw by draw (each admissible draw has its own shocks and loadings). The H.15
yields are recorded earlier in the New York afternoon than the model's prices, so part
of a day's news reaches them the next day; the lags credit that catch-up to the shock
that caused it. ``u_t`` and the intercept are the unspanned part: curve-specific news
the five cross-asset shocks do not represent.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.propagation.data import seal

TENORS = (2, 5, 10, 30)
ACM_TENORS = (2, 5, 10)
LAGS = 2


def load_yields(data_dir="data/raw", *, unseal_holdout: bool = False) -> pd.DataFrame:
    """H.15 constant-maturity yields (percent), columns ``y2, y5, y10, y30``."""
    from giltcurve.ingest.market import load_fred
    out = pd.concat({f"y{t}": load_fred(f"DGS{t}", data_dir, max_age_days=None) for t in TENORS},
                    axis=1, sort=True)
    return seal(out, unseal_holdout=unseal_holdout)


def load_acm_daily(data_dir="data/raw", *, unseal_holdout: bool = False) -> pd.DataFrame:
    """NY Fed daily ACM (percent): fitted yield ``acm{t}``, risk-neutral yield ``rn{t}``
    and term premium ``tp{t}`` at 2, 5 and 10 years."""
    raw = pd.read_excel(Path(data_dir) / "ACMTermPremium.xls", sheet_name="ACM Daily")
    raw["DATE"] = pd.to_datetime(raw["DATE"], format="%d-%b-%Y")
    raw = raw.set_index("DATE").sort_index()
    cols = {}
    for t in ACM_TENORS:
        cols[f"acm{t}"] = raw[f"ACMY{t:02d}"]
        cols[f"rn{t}"] = raw[f"ACMRNY{t:02d}"]
        cols[f"tp{t}"] = raw[f"ACMTP{t:02d}"]
    return seal(pd.DataFrame(cols).astype(float), unseal_holdout=unseal_holdout)


def changes_on(levels: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Changes (bp) between consecutive model days. A day with no quote (a bond-market
    holiday on which equities trade) is NaN and its move folds into the next quoted day,
    so window sums still equal level changes."""
    lv = levels.reindex(dates)
    out = lv.ffill().diff() * 100.0
    return out.mask(lv.isna())


def lagged(eps: np.ndarray, lags: int = LAGS) -> np.ndarray:
    """(T, K*(lags+1)): eps_t, eps_{t-1}, ..., NaN where a lag is unavailable."""
    T, K = eps.shape
    out = np.full((T, K * (lags + 1)), np.nan)
    for s in range(lags + 1):
        out[s:, s * K:(s + 1) * K] = eps[: T - s]
    return out


def fit_loadings(eps: np.ndarray, dy: np.ndarray, lags: int = LAGS) -> np.ndarray:
    """OLS of dy on [1, lagged eps]; returns (1 + K*(lags+1),) coefficients."""
    X = np.column_stack([np.ones(len(dy)), lagged(eps, lags)])
    ok = np.isfinite(dy) & np.isfinite(X).all(1)
    return np.linalg.lstsq(X[ok], dy[ok], rcond=None)[0]


def contributions(eps: np.ndarray, theta: np.ndarray, lags: int = LAGS) -> np.ndarray:
    """(T, K) daily contribution of each shock, summed over its current and lagged terms."""
    K = eps.shape[1]
    X = np.nan_to_num(lagged(eps, lags))
    th = theta[1:].reshape(lags + 1, K)
    return sum(X[:, s * K:(s + 1) * K] * th[s] for s in range(lags + 1))


def impact_signature(theta: np.ndarray, lags: int = LAGS, K: int = 5) -> np.ndarray:
    """Total loading per one-standard-deviation shock (sum over lags), (K,)."""
    return theta[1:].reshape(lags + 1, K).sum(axis=0)


def fit_stats(actual: np.ndarray, fitted: np.ndarray) -> dict:
    """Explanatory R^2 (against the sample mean) and RMSE of fitted against actual changes."""
    ok = np.isfinite(actual) & np.isfinite(fitted)
    a, f = actual[ok], fitted[ok]
    sse = ((a - f) ** 2).sum()
    return {"r2": float(1 - sse / ((a - a.mean()) ** 2).sum()),
            "rmse_bp": float(np.sqrt(sse / ok.sum())),
            "sd_bp": float(a.std()), "n": int(ok.sum())}


def window_sums(x: np.ndarray, n: int) -> np.ndarray:
    """Non-overlapping n-day sums (NaN-propagating)."""
    m = len(x) // n
    return x[: m * n].reshape(m, n, *x.shape[1:]).sum(axis=1)
