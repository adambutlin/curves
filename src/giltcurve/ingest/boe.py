"""Ingest the Bank of England's published SONIA OIS curve (Step 1 / data layer).

The BoE publishes its fitted UK OIS curve daily as an Excel workbook inside
``latest-yield-curve-data.zip``. We download it, parse the spot-rate sheets, and
expose a clean ``(asof, maturities, spot_rates)`` snapshot plus a
:class:`DiscountCurve` builder.

Why this is the right free data source: it is the same curve the MPC and UK
desks look at, the methodology (Anderson-Sleath VRP spline) is published, and it
makes the whole project reproducible without a Bloomberg terminal. A
``bloomberg.py`` adaptor returning the same ``(asof, maturities, rates)`` tuple
would drop straight in for the desk workflow (raw par-swap quotes -> bootstrap).

Sheet layout (verified against the live file):
  row 'years:'  -> maturities in years (column B onward)
  row '#VALUE!'  -> separator
  rows below     -> column A = date, columns B+ = spot rate in **percent**
The same layout serves the spot sheets ('3. spot, short end', '4. spot curve')
and the instantaneous-forward sheets ('1. fwds, short end', '2. fwd curve').
"""
from __future__ import annotations

import datetime as dt
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from giltcurve.curves.discount import DiscountCurve

BOE_LATEST_URL = (
    "https://www.bankofengland.co.uk/-/media/boe/files/statistics/"
    "yield-curves/latest-yield-curve-data.zip"
)
OIS_WORKBOOK = "OIS daily data current month.xlsx"
SHORT_END_SPOT = "3. spot, short end"
SHORT_END_FWD = "1. fwds, short end"
FULL_SPOT = "4. spot curve"


# -- download -----------------------------------------------------------------
def download_boe_zip(dest_dir="data/raw", url: str = BOE_LATEST_URL, force: bool = False) -> Path:
    """Download the latest BoE yield-curve zip (cached unless ``force``)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "latest-yield-curve-data.zip"
    if zip_path.exists() and not force:
        return zip_path
    req = urllib.request.Request(url, headers={"User-Agent": "giltcurve-research/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as fh:
        fh.write(resp.read())
    return zip_path


def extract_ois_workbook(zip_path, dest_dir="data/raw") -> Path:
    """Extract the OIS workbook from the BoE zip; returns its path."""
    dest_dir = Path(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(OIS_WORKBOOK, dest_dir)
    return dest_dir / OIS_WORKBOOK


def ensure_ois_workbook(data_dir="data/raw", force: bool = False) -> Path:
    """Download + extract if needed; returns the path to the OIS workbook."""
    xlsx = Path(data_dir) / OIS_WORKBOOK
    if xlsx.exists() and not force:
        return xlsx
    return extract_ois_workbook(download_boe_zip(data_dir, force=force), data_dir)


# -- parse --------------------------------------------------------------------
def parse_ois_sheet(path, sheet: str) -> pd.DataFrame:
    """Parse a BoE OIS sheet into a DataFrame: index=date, cols=maturity(yrs), decimal."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    col0 = raw.iloc[:, 0]

    yr_rows = col0.astype(str).str.strip().eq("years:")
    if not yr_rows.any():
        raise ValueError(f"could not find a 'years:' header row in sheet {sheet!r}")
    yr_idx = yr_rows.idxmax()
    years = pd.to_numeric(raw.iloc[yr_idx, 1:], errors="coerce").to_numpy(float)

    # Column A mixes header strings with real datetime cells; convert only the
    # genuine date cells to avoid pandas' format-inference fallback warning.
    col_is_date = col0.apply(lambda v: isinstance(v, (dt.datetime, dt.date, pd.Timestamp)))
    dates = pd.to_datetime(col0.where(col_is_date), errors="coerce")
    mask = dates.notna()
    vals = raw.loc[mask, raw.columns[1:]].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    vals = vals / 100.0  # percent -> decimal

    keep = ~np.isnan(years)
    df = pd.DataFrame(vals[:, keep], index=dates[mask], columns=years[keep])
    return df.sort_index()


def latest_spot_curve(spot_df: pd.DataFrame) -> Tuple[dt.date, np.ndarray, np.ndarray]:
    """Most recent dated row -> (asof date, maturities[yrs], spot rates[decimal])."""
    last = spot_df.iloc[-1].dropna()
    asof = spot_df.index[-1]
    asof = asof.date() if hasattr(asof, "date") else asof
    return asof, last.index.to_numpy(float), last.to_numpy(float)


def build_curve_from_spot(maturities, spot_rates, valuation_date) -> DiscountCurve:
    """Continuously-compounded BoE spot rates -> DiscountCurve (D = exp(-R t))."""
    t = np.asarray(maturities, float)
    r = np.asarray(spot_rates, float)
    return DiscountCurve(t, np.exp(-r * t), valuation_date=valuation_date)


def load_latest_curve(data_dir="data/raw", sheet: str = SHORT_END_SPOT, force: bool = False):
    """Convenience: ensure data present, parse ``sheet``, return latest DiscountCurve.

    Returns ``(curve, asof, maturities, spot_rates)``.
    """
    xlsx = ensure_ois_workbook(data_dir, force=force)
    df = parse_ois_sheet(xlsx, sheet)
    asof, mats, spots = latest_spot_curve(df)
    return build_curve_from_spot(mats, spots, asof), asof, mats, spots
