"""US validation-anchor data: the GSW zero curve and NY Fed ACM term premia.

These are the external correctness anchor for the ACM estimator (Step D of the
brief): running our estimator on the Fed Board's Gurkaynak-Sack-Wright (GSW)
zero-coupon curve should reproduce the New York Fed's *published* ACM Treasury
term premia. Both are free public downloads. They are used only for validation;
they are never imported by the core estimator.

Formats verified against the live files (2026-06):

GSW (``feds200628.csv``, served as a plain CSV, NOT .xlsx):
  - The file opens with ~9 lines of metadata/citation text; the header row
    (the one containing the literal substring ``SVENY01``) is at index 9.
    We locate it dynamically rather than hard-coding the row number, since the
    preamble length is not contractually stable.
  - Header row columns include ``BETA0..3``, ``SVEN1F..``, ``SVENF01..30``
    (instantaneous forwards), ``SVENPY01..30`` (par yields) and
    ``SVENY01..30`` (zero/spot yields) -- the two-digit suffix runs 01..30,
    so ``col[5:].isdigit()`` correctly captures all of them.
  - Missing observations are the literal string ``"NA"`` (not blank).
  - Values are in **percent** (e.g. ``4.08`` for 4.08%), so the loader
    divides by 100 to return decimals.
  - First column is ``Date``, format ``YYYY-MM-DD``.

NY Fed ACM workbook (``ACMTermPremium.xls``):
  - This is served as a genuine legacy OLE2 ``.xls`` binary (magic bytes
    ``D0 CF 11 E0``), not an ``.xlsx`` despite many sites assuming otherwise.
    Reading it with ``pandas.read_excel`` requires the optional ``xlrd``
    package (added as a project dependency); ``openpyxl`` alone cannot read
    legacy ``.xls``.
  - ``pd.ExcelFile`` reports two sheets: ``"ACM Monthly"`` (first/default) and
    ``"ACM Daily"``. We use the first sheet (monthly), matching the NY Fed's
    primary published series and giving the long history the tests expect.
  - Columns are ``DATE`` plus ``ACMY01..10`` (fitted yield), ``ACMTP01..10``
    (term premium), ``ACMRNY01..10`` (risk-neutral yield) -- two-digit tenor
    suffixes 01..10, so ``col[len(prefix):].isdigit()`` and
    ``float("01") == 1.0`` work as in the reference implementation.
  - Values are in **percent** (e.g. ``ACMTP10`` of ``0.17`` means 0.17%), so
    the loader divides by 100 to return decimals.
  - Dates are Excel-native datetimes (e.g. ``30-Jun-1961``) in the first
    column, named ``DATE``.
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import pandas as pd

GSW_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
NYFED_ACM_URL = (
    "https://www.newyorkfed.org/medialibrary/media/research/"
    "data_indicators/ACMTermPremium.xls"
)
ACM_SHEET = "ACM Monthly"
_UA = {"User-Agent": "giltcurve-research/0.1"}


def _get(url: str, dest: Path, force: bool) -> bytes:
    if dest.exists() and not force:
        return dest.read_bytes()
    req = urllib.request.Request(url, headers=_UA)
    raw = urllib.request.urlopen(req, timeout=60).read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return raw


def download_gsw(data_dir="data/raw", force: bool = False) -> Path:
    dest = Path(data_dir) / "feds200628.csv"
    _get(GSW_URL, dest, force)
    return dest


def download_nyfed_acm(data_dir="data/raw", force: bool = False) -> Path:
    dest = Path(data_dir) / "ACMTermPremium.xls"
    _get(NYFED_ACM_URL, dest, force)
    return dest


def load_gsw_panel(data_dir="data/raw", force: bool = False, max_tenor: int = 10) -> pd.DataFrame:
    """GSW continuously-compounded zero yields -> panel (date x maturity[yrs], decimal).

    The CSV carries a metadata preamble; the header row is located dynamically
    as the one containing ``SVENY01``. Columns ``SVENY01..SVENY{N}`` are
    annual zero yields in percent, with missing values coded as ``"NA"``.
    """
    path = download_gsw(data_dir, force)
    text = path.read_text("utf-8", "replace").splitlines()
    hits = [i for i, line in enumerate(text) if "SVENY01" in line]
    if not hits:
        raise ValueError("could not find a 'SVENY01' header row in the GSW CSV")
    hdr = hits[0]
    df = pd.read_csv(io.StringIO("\n".join(text[hdr:])), na_values=["NA"])
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    cols = {c: int(c.replace("SVENY", "")) for c in df.columns
            if c.startswith("SVENY") and c[5:].isdigit()}
    keep = {y: c for c, y in cols.items() if y <= max_tenor}
    out = df[list(keep.values())].apply(pd.to_numeric, errors="coerce") / 100.0
    out.columns = [float(y) for y in keep.keys()]
    return out.reindex(sorted(out.columns), axis=1)


def load_nyfed_acm(data_dir="data/raw", force: bool = False) -> pd.DataFrame:
    """NY Fed ACM workbook -> tidy frame index=date, MultiIndex cols (kind, tenor).

    kind in {"yield","term_premium","risk_neutral"} from ACMY/ACMTP/ACMRNY.
    The workbook is a legacy OLE2 ``.xls``; reading it requires the optional
    ``xlrd`` dependency (pandas cannot use ``openpyxl`` for ``.xls``).
    """
    path = download_nyfed_acm(data_dir, force)
    raw = pd.read_excel(path, sheet_name=ACM_SHEET)
    date_col = raw.columns[0]
    raw[date_col] = pd.to_datetime(raw[date_col], errors="coerce")
    raw = raw.dropna(subset=[date_col]).set_index(date_col).sort_index()
    kind_map = {"ACMTP": "term_premium", "ACMRNY": "risk_neutral", "ACMY": "yield"}
    tuples, data = [], {}
    for col in raw.columns:
        for prefix, kind in kind_map.items():
            if col.startswith(prefix) and col[len(prefix):].isdigit():
                tenor = float(col[len(prefix):])
                tuples.append((kind, tenor))
                data[(kind, tenor)] = pd.to_numeric(raw[col], errors="coerce") / 100.0
                break
    out = pd.DataFrame(data)
    out.columns = pd.MultiIndex.from_tuples(out.columns, names=["kind", "tenor"])
    return out


def nyfed_term_premium(acm: pd.DataFrame, tenor: float = 10.0) -> pd.Series:
    """Published NY Fed term-premium series at a tenor (years), decimal."""
    return acm["term_premium"][float(tenor)]
