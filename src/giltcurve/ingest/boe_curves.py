"""Parameterised loader for the four Bank of England daily curve archives.

The BoE publishes nominal gilt, real gilt, implied-inflation and SONIA OIS
curves as separate zip archives that share one sheet layout, so a single
loader parameterised by ``kind`` covers all four. This supersedes the
nominal-only ``ingest/boe_gilt.py``, whose public functions still work.

Each kind needs two downloads: the multi-decade history archive (updated
roughly fortnightly) and ``latest-yield-curve-data.zip`` (the current month).
Merging both is what gets you data right up to yesterday.

Quirks verified against the live site (2026-08-20/21):
  * ``latest-yield-curve-data.zip`` is usually flat but is occasionally served
    with an inner zip; ``_extract_member`` handles both.
  * The spot-curve sheet name varies by kind AND by vintage, not just by the
    nominal/pre-2005 split documented in ``boe_gilt.py``. Verified sheet names
    across every history workbook and the current-month workbook:
      - nominal:   "4. nominal spot curve" (pre-2005) / "4. spot curve" (2005+)
      - real:      "4.  real spot curve"   (pre-2005, note the double space)
                   / "4. spot curve" (2005+)
      - inflation: "4.  inf spot curve"    (pre-2005, double space)
                   / "4. spot curve" (2005+)
      - ois:       "2. spot curve" (2009-2015; this vintage has no short-end
                   split, only "1. fwd curve" / "2. spot curve") / "4. spot
                   curve" (2016+)
    Rather than hardcode five brittle literal strings (one of which relies on
    reproducing an inconsistent double space), ``_resolve_spot_sheet`` matches
    sheet names by pattern: whitespace-normalise, then accept ``"<n>. [prefix
    ]spot curve"`` for any leading sheet number and optional nominal/real/inf
    prefix. This is derived from live inspection of every workbook, not a
    guess. It raises if more than one sheet matches, rather than silently
    picking whichever came first.
  * The history archive refreshes fortnightly, same as the current-month
    archive refreshes daily -- both determine currency, so both need a
    freshness check rather than indefinite caching. ``download_history``
    passes ``max_age_days=1`` to ``fetch``.
  * Pre-2016 OIS workbooks carry tenor values with float rounding noise
    (e.g. ``0.49999999999999994`` alongside 2016+'s exact ``0.5``), so a
    naive concat of vintages produces duplicate tenor columns and a
    non-monotonic column index. ``_tidy_tenor_columns`` collapses columns
    that agree to 6dp and sorts the result; applied to every kind, since
    nominal/real/inflation are only accidentally sorted today by having
    uniform tenor grids across vintages. Note the OIS panel is genuinely not
    a rectangle: pre-2016 rows have nothing beyond 5y (that vintage's curve
    stops there) and post-2016 rows have nothing below 0.5y (the short end
    lives on sheet 3 and is correctly excluded here).
  * Values are in percent; ``parse_ois_sheet`` converts to decimals.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from giltcurve.ingest._http import fetch
from giltcurve.ingest.boe import parse_ois_sheet

BASE_URL = "https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves"
LATEST_ARCHIVE = "latest-yield-curve-data.zip"

# Matches "4. spot curve", "4. nominal spot curve", "4.  real spot curve"
# (any run of whitespace), "4.  inf spot curve", "2. spot curve" (the OIS
# 2009-2015 vintage, which has no short-end sheets and numbers spot curve 2
# rather than 4) -- every spot-curve sheet name observed across all four
# kinds and all vintages, live-verified rather than assumed.
_SPOT_SHEET_RE = re.compile(r"^\d+\.\s+(?:nominal\s+|real\s+|inf\s+)?spot curve$")


@dataclass(frozen=True)
class CurveSpec:
    archive: str              # history zip file name
    workbook_token: str       # substring identifying this kind's workbooks
    current_month_member: str  # member name inside LATEST_ARCHIVE


KIND_SPEC = {
    "nominal": CurveSpec("glcnominalddata.zip", "Nominal",
                         "GLC Nominal daily data current month.xlsx"),
    "real": CurveSpec("glcrealddata.zip", "Real",
                      "GLC Real daily data current month.xlsx"),
    "inflation": CurveSpec("glcinflationddata.zip", "Inflation",
                           "GLC Inflation daily data current month.xlsx"),
    "ois": CurveSpec("oisddata.zip", "OIS",
                     "OIS daily data current month.xlsx"),
}
CURVE_KINDS = tuple(KIND_SPEC)


def _spec(kind: str) -> CurveSpec:
    try:
        return KIND_SPEC[kind]
    except KeyError:
        raise ValueError(
            f"unknown curve kind {kind!r}; expected one of {CURVE_KINDS}"
        ) from None


def _extract_member(zip_path: Path, dest_dir: Path, predicate) -> list[Path]:
    """Extract members matching ``predicate``, descending into an inner zip if needed."""
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if predicate(n)]
        for name in names:
            out.append(Path(zf.extract(name, dest_dir)))
        if out:
            return out
        for inner in (n for n in zf.namelist() if n.endswith(".zip")):
            with zipfile.ZipFile(io.BytesIO(zf.read(inner))) as zf2:
                for name in (n for n in zf2.namelist() if predicate(n)):
                    out.append(Path(zf2.extract(name, dest_dir)))
    return out


def download_history(kind: str, data_dir="data/raw", force: bool = False) -> list[Path]:
    """Download + extract the multi-decade history archive for ``kind``.

    The archive refreshes roughly fortnightly, so a cached copy older than a
    day is treated as stale and re-fetched (``max_age_days=1``) -- otherwise
    an indefinitely-cached copy can silently leave a multi-week hole between
    the end of history and the start of the current-month workbook.
    """
    spec = _spec(kind)
    data_dir = Path(data_dir)
    zip_path = data_dir / spec.archive
    fetch(f"{BASE_URL}/{spec.archive}", zip_path, force=force, max_age_days=1)
    return _extract_member(
        zip_path, data_dir,
        lambda n: spec.workbook_token in n and n.endswith(".xlsx"),
    )


def download_current_month(kind: str, data_dir="data/raw") -> list[Path]:
    """Download + extract the current-month workbook for ``kind``.

    Always refreshes: this archive is the whole point of being current, so
    there is no ``force`` parameter to ignore.
    """
    spec = _spec(kind)
    data_dir = Path(data_dir)
    zip_path = data_dir / LATEST_ARCHIVE
    fetch(f"{BASE_URL}/{LATEST_ARCHIVE}", zip_path, force=True)
    return _extract_member(
        zip_path, data_dir,
        lambda n: n.endswith(spec.current_month_member),
    )


def _resolve_spot_sheet(path: Path, sheet: str | None) -> str:
    if sheet is not None:
        return sheet
    names = pd.ExcelFile(path).sheet_names
    matches = [
        name for name in names
        if _SPOT_SHEET_RE.match(re.sub(r"\s+", " ", name.strip()))
    ]
    if not matches:
        raise ValueError(f"no spot-curve sheet found in {path}; sheets={names}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous spot-curve sheet in {path}: matches={matches}")
    return matches[0]


def _tidy_tenor_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse float-noise duplicate tenor columns and sort columns ascending.

    Pre-2016 OIS workbooks carry tenor values that are equal to 2016+'s to
    within float noise but not exactly (``0.49999999999999994`` vs ``0.5``),
    so concatenating vintages produces duplicate columns under exact float
    equality. Rounding to 6dp before grouping collapses these; the vintages
    are non-overlapping in date range, so at most one of the duplicate
    columns is non-NaN for any given row, and ``GroupBy.first()`` keeps
    whichever one has the value.
    """
    if df.empty:
        return df
    tidy = df.copy()
    tidy.columns = np.round(np.asarray(tidy.columns, dtype=float), 6)
    tidy = tidy.T.groupby(level=0).first().T
    return tidy.sort_index(axis=1)


def merge_panels(history: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Concatenate, letting ``current`` win on shared dates, then drop empty rows.

    Dedupes BEFORE sorting: ``concat`` order (history then current) is
    guaranteed, but ``sort_index``'s default quicksort is unstable, so
    deduping after sorting would let ``keep="last"`` pick arbitrarily between
    a history row and a current row that land on the same timestamp --
    silently preferring the stale history value roughly half the time.
    """
    panel = pd.concat([history, current])
    panel = panel[~panel.index.duplicated(keep="last")]
    return panel.sort_index().dropna(how="all")


def load_curve(kind: str, data_dir="data/raw", sheet: str | None = None,
               force: bool = False) -> pd.DataFrame:
    """Full daily panel for ``kind``: index=date, columns=maturity(years), decimal."""
    spec = _spec(kind)
    hist_files = download_history(kind, data_dir, force=force)
    cur_files = download_current_month(kind, data_dir)
    if not hist_files:
        raise FileNotFoundError(f"no {spec.workbook_token!r} workbooks in {spec.archive}")
    if not cur_files:
        raise FileNotFoundError(
            f"no {spec.current_month_member!r} member in {LATEST_ARCHIVE}"
        )

    def _read(paths):
        frames = [parse_ois_sheet(p, _resolve_spot_sheet(p, sheet)) for p in paths]
        return pd.concat(frames).sort_index() if frames else pd.DataFrame()

    merged = merge_panels(_read(sorted(hist_files)), _read(cur_files))
    return _tidy_tenor_columns(merged)
