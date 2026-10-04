"""Free daily market data for the cross-Atlantic model: equity indices, rates, FX, volatility.

Sources (all free, no key; verified 4 October 2026):

- **Yahoo Finance chart service** for index levels that have no free official daily
  history: Euro Stoxx 50 (``^STOXX50E``), S&P 500 (``^GSPC``) and the ICE BofA MOVE
  index of Treasury implied volatility (``^MOVE``). The JSON carries epoch timestamps
  at the market open; they are converted to the exchange's local calendar date. The
  service rejects non-browser user agents, so it is fetched with ``curl`` and a browser
  agent string rather than through :func:`giltcurve.ingest._http.fetch`.
- **Bundesbank** daily Svensson zero-coupon yields on Federal securities (Bunds), the
  free stand-in for the euro-area 10-year OIS rate. The CSV has an 8-row preamble and
  ``.`` for missing values.
- **FRED** without a key for VIX (``VIXCLS``) and the dollar price of a euro
  (``DEXUSEU``).

Every loader caches to ``data_dir`` and refreshes files older than ``max_age_days``.
None of them seals the 2026 holdout; the panel builders do that.
"""
from __future__ import annotations

import io
import json
import subprocess
import time
from pathlib import Path

import pandas as pd

from giltcurve.ingest._http import fetch

YAHOO_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
             "?period1=631152000&period2={end}&interval=1d")
BUNDESBANK_URL = ("https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
                  "D.I.ZST.ZI.EUR.S1311.B.A604.R{tenor:02d}XX.R.A.A._Z._Z.A?format=csv&lang=en")
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
_BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15"


def _stale(path: Path, max_age_days: float | None) -> bool:
    if not path.exists():
        return True
    if max_age_days is None:
        return False
    return (time.time() - path.stat().st_mtime) / 86400 > max_age_days


def _yahoo_download(symbol: str, dest: Path, timeout: int = 120) -> None:
    url = YAHOO_URL.format(symbol=symbol.replace("^", "%5E"), end=int(time.time()))
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["curl", "-sSLf", "--max-time", str(timeout), "-A", _BROWSER_UA,
                           "-o", str(tmp), url], capture_output=True, text=True)
    if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Yahoo download failed for {symbol}: {proc.stderr.strip()}")
    tmp.replace(dest)


def parse_yahoo_chart(payload: dict) -> pd.Series:
    """Daily closes from a Yahoo chart JSON payload, indexed by local exchange date."""
    res = payload["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName", "UTC")
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    close = pd.Series(res["indicators"]["quote"][0]["close"], index=ts.tz_localize(None).normalize(),
                      dtype=float)
    close = close[~close.index.duplicated(keep="last")].dropna()
    close.index.name = "date"
    return close.sort_index()


def load_yahoo_close(symbol: str, data_dir: str | Path = "data/raw", *,
                     max_age_days: float | None = 1.0) -> pd.Series:
    dest = Path(data_dir) / f"yahoo_{symbol.replace('^', '')}.json"
    if _stale(dest, max_age_days):
        _yahoo_download(symbol, dest)
    return parse_yahoo_chart(json.loads(dest.read_text())).rename(symbol)


def parse_bundesbank_csv(text: str) -> pd.Series:
    """Bundesbank time-series CSV: preamble rows, then ``date,value,flag``; '.' is missing."""
    rows = [line for line in text.splitlines() if line[:4].isdigit() and line[4:5] == "-"]
    df = pd.read_csv(io.StringIO("\n".join(rows)), header=None, usecols=[0, 1],
                     names=["date", "value"], na_values=["."])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].astype(float).dropna().sort_index()


def load_bund_zero(tenor_years: int = 10, data_dir: str | Path = "data/raw", *,
                   max_age_days: float | None = 1.0) -> pd.Series:
    """Bundesbank Svensson zero-coupon Bund yield, percent."""
    path = fetch(BUNDESBANK_URL.format(tenor=tenor_years),
                 Path(data_dir) / f"bundesbank_zero_{tenor_years:02d}y.csv", max_age_days=max_age_days)
    return parse_bundesbank_csv(path.read_text("utf-8-sig")).rename(f"bund{tenor_years}")


def load_fred(series: str, data_dir: str | Path = "data/raw", *,
              max_age_days: float | None = 1.0) -> pd.Series:
    path = fetch(FRED_URL.format(series=series), Path(data_dir) / f"fred_{series}.csv",
                 max_age_days=max_age_days)
    df = pd.read_csv(path, na_values=["."])
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col)[series].astype(float).dropna().sort_index()
