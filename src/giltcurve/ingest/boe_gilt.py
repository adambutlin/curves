"""Ingest the Bank of England published NOMINAL gilt zero-coupon curve.

ACM decomposes the *government bond* curve, so this loads the BoE Anderson-Sleath
nominal-gilt spot curve (daily, from 1979) from the same yield-curves source as
the SONIA OIS curve. It reuses the sheet-parsing mechanics of ``ingest/boe.py``
(``years:`` header row; column A = dates mixed with header strings; values in
percent). The SONIA OIS curve is NOT decomposed here — it is the expectations
anchor in the validation step (``policy/meeting_dated.py``).

Two quirks discovered against the live BoE site (2026-06):

1. ``latest-yield-curve-data.zip`` is sometimes a *flat* zip containing the four
   "current month" workbooks directly, and sometimes a *nested* zip (the BoE's
   CDN occasionally serves an inner
   ``Latest Yield Curve data (current month).zip`` alongside some ``.gif``
   assets). ``extract_gilt_workbook`` handles both shapes.
2. The "4. spot curve" sheet was renamed at some point: the pre-2005 history
   workbooks (1979-2004) call it **"4. nominal spot curve"**; 2005-onwards
   workbooks (including the current-month file) call it **"4. spot curve"**.
   ``_resolve_spot_sheet`` tries both names.

History: ACM needs decades of monthly data, but the current-month workbook in
``latest-yield-curve-data.zip`` only contains ~1 month of daily data (roughly
one monthly observation) -- nowhere near enough to fit ACM. The BoE separately
publishes the full nominal-gilt history (1979 to present, daily) as
``glcnominalddata.zip`` on the yield-curves page
(https://www.bankofengland.co.uk/statistics/yield-curves), split into 8
workbooks covering 1979-1984, 1985-1989, 1990-1994, 1995-1999, 2000-2004,
2005-2015, 2016-2024 and 2025-present. ``download_gilt_history`` fetches and
extracts this archive into ``data_dir``; after calling it, ``load_gilt_history``
concatenates every nominal workbook found there into one multi-decade panel.
"""
from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.ingest.boe import download_boe_zip, parse_ois_sheet
from giltcurve.curves.discount import DiscountCurve

GILT_WORKBOOK = "GLC Nominal daily data current month.xlsx"
SPOT_SHEET = "4. spot curve"
SPOT_SHEET_ALIASES = (SPOT_SHEET, "4. nominal spot curve")

HISTORY_URL = (
    "https://www.bankofengland.co.uk/-/media/boe/files/statistics/"
    "yield-curves/glcnominalddata.zip"
)


# -- download / extract (current month) ---------------------------------------
def extract_gilt_workbook(zip_path, dest_dir="data/raw", member=GILT_WORKBOOK) -> Path:
    """Extract the nominal-gilt workbook from the BoE latest-yield-curve zip.

    Handles both the flat zip layout (workbooks directly inside) and the
    occasional nested layout (an inner
    ``Latest Yield Curve data (current month).zip`` containing the workbooks).
    """
    dest_dir = Path(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if member in names:
            zf.extract(member, dest_dir)
            return dest_dir / member

        nominal = [n for n in names if "Nominal" in n and n.endswith(".xlsx")]
        if nominal:
            zf.extract(nominal[0], dest_dir)
            return dest_dir / nominal[0]

        # Nested zip: find an inner .zip member and recurse into it.
        inner_names = [n for n in names if n.endswith(".zip")]
        if not inner_names:
            raise FileNotFoundError(
                f"no nominal-gilt workbook or inner zip found in {zip_path}; "
                f"members={names}"
            )
        inner_bytes = zf.read(inner_names[0])
        with zipfile.ZipFile(io.BytesIO(inner_bytes)) as zf2:
            inner_member_names = zf2.namelist()
            target = member if member in inner_member_names else next(
                n for n in inner_member_names if "Nominal" in n and n.endswith(".xlsx")
            )
            zf2.extract(target, dest_dir)
            return dest_dir / target


def ensure_gilt_workbook(data_dir="data/raw", force: bool = False) -> Path:
    """Download + extract if needed; returns the path to the current-month nominal workbook."""
    data_dir = Path(data_dir)
    xlsx = data_dir / GILT_WORKBOOK
    if xlsx.exists() and not force:
        return xlsx
    zp = download_boe_zip(data_dir, force=force)
    return extract_gilt_workbook(zp, data_dir)


# -- download / extract (multi-decade history) ---------------------------------
def download_gilt_history(data_dir="data/raw", force: bool = False) -> list[Path]:
    """Download + extract the full BoE nominal-gilt history archive (1979-present).

    Source: ``glcnominalddata.zip`` on the BoE yield-curves page, currently
    split into 8 workbooks (1979-1984, 1985-1989, 1990-1994, 1995-1999,
    2000-2004, 2005-2015, 2016-2024, 2025-present). Returns the list of
    extracted workbook paths.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = data_dir / "glcnominalddata.zip"
    if not zip_path.exists() or force:
        req = urllib.request.Request(
            HISTORY_URL, headers={"User-Agent": "giltcurve-research/0.1"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as fh:
            fh.write(resp.read())

    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if "Nominal" in name and name.endswith(".xlsx"):
                target = data_dir / name
                if force or not target.exists():
                    zf.extract(name, data_dir)
                extracted.append(target)
    return extracted


# -- parse ----------------------------------------------------------------------
def _resolve_spot_sheet(path, sheet: str) -> str:
    """Return whichever spot-sheet name actually exists in ``path``.

    The sheet was renamed from "4. nominal spot curve" (pre-2005 history
    workbooks) to "4. spot curve" (2005-onwards, including current-month).
    """
    if sheet in SPOT_SHEET_ALIASES:
        names = pd.ExcelFile(path).sheet_names
        for candidate in SPOT_SHEET_ALIASES:
            if candidate in names:
                return candidate
        raise ValueError(f"none of {SPOT_SHEET_ALIASES!r} found as a sheet in {path}")
    return sheet


def load_gilt_panel(data_dir="data/raw", sheet=SPOT_SHEET, force: bool = False) -> pd.DataFrame:
    """Parse the current nominal-gilt spot sheet -> panel (date x maturity, decimal)."""
    xlsx = ensure_gilt_workbook(data_dir, force=force)
    resolved = _resolve_spot_sheet(xlsx, sheet)
    panel = parse_ois_sheet(xlsx, resolved)
    return panel.dropna(how="all")


def load_gilt_history(data_dir="data/raw", sheet=SPOT_SHEET) -> pd.DataFrame:
    """Concatenate every nominal-gilt workbook found in ``data_dir`` into one panel.

    Keeps the last occurrence of any duplicated date. Used for the multi-decade
    ACM estimation panel. Call ``download_gilt_history`` first to populate
    ``data_dir`` with the full 1979-present archive.
    """
    files = sorted(Path(data_dir).glob("*Nominal*.xlsx"))
    if not files:
        raise FileNotFoundError("no '*Nominal*.xlsx' gilt workbooks in data dir")
    frames = []
    for f in files:
        resolved = _resolve_spot_sheet(f, sheet)
        frames.append(parse_ois_sheet(f, resolved))
    panel = pd.concat(frames).sort_index()
    panel = panel[~panel.index.duplicated(keep="last")]
    return panel.dropna(how="all")


def latest_gilt_curve(data_dir="data/raw", force: bool = False) -> DiscountCurve:
    """Most recent nominal-gilt spot row -> DiscountCurve (D = exp(-R t))."""
    panel = load_gilt_panel(data_dir, force=force)
    last = panel.iloc[-1].dropna()
    asof = panel.index[-1]
    asof = asof.date() if hasattr(asof, "date") else asof
    t = last.index.to_numpy(float)
    r = last.to_numpy(float)
    return DiscountCurve(t, np.exp(-r * t), valuation_date=asof)
