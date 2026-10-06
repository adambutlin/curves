"""Synchronised euro-area prices from LSEG (Refinitiv) Workspace.

Why: European cash markets close about five and a half hours before New York, so
close-to-close daily data let euro-area prices catch up the next day with US afternoon
news (next-day Bund on today's Treasury: 0.40 with the Bundesbank curve). Eurex futures
trade until 22:00 Frankfurt time, which is the New York close, and Refinitiv's FX and OIS
composites close late in the evening, so these series are (close to) synchronised with
US closes. Measured on 1999-2025, the next-day coefficient on today's Treasury move is
0.02 for the Bund future's last trade, 0.07 for the 10-year OIS composites and -0.05 for
the Euro Stoxx 50 future's last trade (against 0.24 for the cash EURO STOXX index).

Access: a running Workspace desktop session and an app key in the ``LSEG_APP_KEY``
environment variable. The key is never written to disk. Downloads are cached in
``data_dir`` (git-ignored: licensed data are not redistributed).

Futures continuation series (``c1``) jump when the front contract changes. Roll days
come from the exchange calendar (Euro Stoxx 50: expiry on the third Friday of March,
June, September and December; Euro Bund: last trading day two exchange days before the
10th of those months), and on a roll day the return is measured within one contract,
``log(c1_t / c2_{t-1})``, because today's front contract was yesterday's second.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

QUARTER_MONTHS = (3, 6, 9, 12)


# ---------------------------------------------------------------- access
def _session(port: int | None = None):
    import lseg.data as ld
    cfg = ld.get_config()
    cfg.set_param("logs.level", "error")
    if port is not None:
        cfg.set_param("sessions.desktop.workspace.base-url", f"http://127.0.0.1:{port}")
    key = os.environ.get("LSEG_APP_KEY")
    if not key:
        raise RuntimeError("set LSEG_APP_KEY (a Workspace app key) in the environment")
    session = ld.session.desktop.Definition(app_key=key).get_session()
    ld.session.set_default(session)
    session.open()
    return ld


def fetch_history(ric: str, fields: list[str], data_dir="data/raw", *, start="1998-12-01",
                  end=None, port: int | None = 9001, refresh: bool = False) -> pd.DataFrame:
    """Daily history of ``fields`` for one RIC, cached as ``data_dir/lseg_<ric>.csv``."""
    dest = Path(data_dir) / f"lseg_{ric.replace('=', '_').replace('.', '')}.csv"
    if dest.exists() and not refresh:
        cached = pd.read_csv(dest, index_col=0, parse_dates=True)
        if set(fields) <= set(cached.columns):
            return cached[fields]
    ld = _session(port)
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    parts, errors = [], []
    for a, b in (("1998-12-01", "2006-12-31"), ("2007-01-01", "2014-12-31"), ("2015-01-01", end)):
        if pd.Timestamp(b) < pd.Timestamp(start):
            continue
        try:
            parts.append(ld.get_history(universe=ric, fields=fields, interval="daily",
                                        start=max(a, start), end=b))
        except Exception as exc:          # a chunk before the series starts returns no data
            errors.append(str(exc)[:200])
    ld.close_session()
    if not parts:
        raise RuntimeError(f"no LSEG data for {ric} {fields}: {errors}")
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.columns = [str(c) for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce")
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest)
    return df[fields]


# ---------------------------------------------------------------- futures rolls
def third_friday(year: int, month: int) -> pd.Timestamp:
    first = pd.Timestamp(year, month, 1)
    return first + pd.Timedelta(days=(4 - first.weekday()) % 7 + 14)


def roll_days(trading_days: pd.DatetimeIndex, contract: str) -> pd.DatetimeIndex:
    """First trading day after each quarterly expiry, on the series' own calendar.

    ``contract``: ``"fesx"`` (Euro Stoxx 50; expiry on the third Friday, or the previous
    trading day if that is a holiday) or ``"fgbl"`` (Euro Bund; delivery on the 10th or
    the next trading day, last trading day two trading days earlier).
    """
    days = pd.DatetimeIndex(sorted(trading_days))
    out = []
    for year in range(days.min().year, days.max().year + 1):
        for m in QUARTER_MONTHS:
            if contract == "fesx":
                last = days[days <= third_friday(year, m)]
                if len(last) == 0:
                    continue
                expiry_pos = days.get_loc(last[-1])
            elif contract == "fgbl":
                deliv = days[days >= pd.Timestamp(year, m, 10)]
                if len(deliv) == 0:
                    continue
                expiry_pos = days.get_loc(deliv[0]) - 2
            else:
                raise ValueError(contract)
            if 0 <= expiry_pos < len(days) - 1:
                out.append(days[expiry_pos + 1])
    return pd.DatetimeIndex(out)


def roll_adjusted_log_level(c1: pd.Series, c2: pd.Series, contract: str) -> pd.Series:
    """Cumulative within-contract log return (percent) of a futures continuation."""
    c1, c2 = c1.dropna(), c2.reindex(c1.index).ffill()
    r = np.log(c1).diff()
    rolls = roll_days(c1.index, contract)
    rolls = rolls[rolls.isin(c1.index)]
    prev = c1.index.get_indexer(rolls) - 1
    ok = prev >= 0
    r.loc[rolls[ok]] = np.log(c1.loc[rolls[ok]].to_numpy() / c2.iloc[prev[ok]].to_numpy())
    return (r.fillna(0.0).cumsum() * 100.0).rename(f"{contract}_log")
