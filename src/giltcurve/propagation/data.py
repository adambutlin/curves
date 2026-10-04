"""Daily US cross-asset panel with the 2026 holdout sealed.

The panel holds the Gürkaynak-Sack-Wright 2-, 5- and 10-year zero-coupon yields
and the US value-weighted equity market return on the trading days common to
both markets. Changes are taken between consecutive common days, so a day on
which only one market trades folds into the next common day rather than
producing a spurious zero.

Every observation dated on or after ``HOLDOUT_START`` is removed *before* any
transformation, unless the caller passes ``unseal_holdout=True``. Asking for an
end date inside the holdout without unsealing raises, so a sealed run cannot
silently see 2026 (pre-registration, Section 8).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.ingest._http import fetch

HOLDOUT_START = pd.Timestamp("2026-01-01")
SAMPLE_START = pd.Timestamp("1983-01-03")
TENORS = (2, 5, 10)

FRENCH_DAILY_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)
GSW_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"


class HoldoutSealedError(RuntimeError):
    """Raised when a sealed run asks for observations inside the holdout."""


def seal(frame: pd.DataFrame | pd.Series, *, unseal_holdout: bool = False):
    """Drop every observation dated on or after ``HOLDOUT_START`` unless unsealed."""
    if unseal_holdout:
        return frame
    return frame.loc[frame.index < HOLDOUT_START]


def load_gsw_zero_yields(data_dir: str | Path = "data/raw", *, unseal_holdout: bool = False,
                         tenors=TENORS) -> pd.DataFrame:
    """GSW zero-coupon yields in percent, columns ``y2, y5, y10`` (by default).

    The Board's CSV opens with a citation preamble; the header is the first row
    containing ``SVENY01``. Missing values are the literal ``NA``.
    """
    path = fetch(GSW_URL, Path(data_dir) / "feds200628.csv")
    lines = path.read_text("utf-8", "replace").splitlines()
    hdr = next(i for i, line in enumerate(lines) if "SVENY01" in line)
    raw = pd.read_csv(io.StringIO("\n".join(lines[hdr:])), na_values=["NA"])
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw = raw.dropna(subset=["Date"]).set_index("Date").sort_index()
    raw = seal(raw, unseal_holdout=unseal_holdout)
    out = pd.DataFrame({f"y{n}": pd.to_numeric(raw[f"SVENY{n:02d}"], errors="coerce")
                        for n in tenors})
    return out.dropna()


def load_french_market_return(data_dir: str | Path = "data/raw", *,
                              unseal_holdout: bool = False) -> pd.Series:
    """Daily US value-weighted market total return (``Mkt-RF + RF``), percent.

    The zipped CSV has a short text preamble, a header row ``,Mkt-RF,SMB,HML,RF``,
    one row per trading day keyed ``YYYYMMDD``, then a blank line and a copyright
    footer.
    """
    path = fetch(FRENCH_DAILY_URL, Path(data_dir) / "ff_factors_daily.zip")
    with zipfile.ZipFile(path) as zf:
        text = zf.read(zf.namelist()[0]).decode("latin-1")
    rows = [line for line in text.splitlines()
            if line.strip()[:8].isdigit() and "," in line]
    df = pd.read_csv(io.StringIO("\n".join(rows)), header=None,
                     names=["date", "mkt_rf", "smb", "hml", "rf"])
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    df = df.set_index("date").sort_index()
    df = seal(df, unseal_holdout=unseal_holdout)
    return (df["mkt_rf"] + df["rf"]).rename("eq_simple_pct")


def build_panel(yields: pd.DataFrame, equity_simple_pct: pd.Series, *,
                start: str | pd.Timestamp = SAMPLE_START,
                end: str | pd.Timestamp = HOLDOUT_START - pd.Timedelta(days=1),
                unseal_holdout: bool = False) -> pd.DataFrame:
    """Align yields and equity on common trading days and form daily changes.

    Returns levels ``y2, y5, y10`` (percent), changes ``dy2, dy5, dy10`` (basis
    points) and the equity log return ``req`` (percent), indexed by date. The
    first common day has no change and is dropped.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end >= HOLDOUT_START and not unseal_holdout:
        raise HoldoutSealedError(
            f"end={end.date()} lies inside the sealed holdout (from {HOLDOUT_START.date()}); "
            "pass unseal_holdout=True only under the pre-registered protocol")
    yields = seal(yields, unseal_holdout=unseal_holdout)
    equity_simple_pct = seal(equity_simple_pct, unseal_holdout=unseal_holdout)

    cum_log_eq = np.log1p(equity_simple_pct / 100.0).cumsum() * 100.0
    common = yields.dropna().index.intersection(cum_log_eq.index)
    lv = yields.loc[common].sort_index()
    eq = cum_log_eq.loc[common].sort_index()
    out = lv.copy()
    for col in lv.columns:
        out["d" + col] = lv[col].diff() * 100.0
    out["req"] = eq.diff()
    out = out.iloc[1:]
    return out.loc[(out.index >= start) & (out.index <= end)]


def load_us_panel(data_dir: str | Path = "data/raw", *, start=SAMPLE_START,
                  end=HOLDOUT_START - pd.Timedelta(days=1),
                  unseal_holdout: bool = False) -> pd.DataFrame:
    """The pre-registered estimation panel (1983-2025 by default)."""
    ylds = load_gsw_zero_yields(data_dir, unseal_holdout=unseal_holdout)
    eq = load_french_market_return(data_dir, unseal_holdout=unseal_holdout)
    return build_panel(ylds, eq, start=start, end=end, unseal_holdout=unseal_holdout)
