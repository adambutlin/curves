"""Cached HTTP fetch with a curl fallback.

Python's ``urllib`` times out connecting to the Bank of England CDN in some
sandboxed environments while ``curl`` succeeds on the identical URL (verified
2026-08-20). Every ingest adaptor therefore goes through :func:`fetch`, which
tries ``urllib`` first and falls back to the ``curl`` binary.

Downloads are written to a temporary sibling and moved into place only on
success, so a failed fetch never leaves a truncated file that a later cached
read would happily return -- this covers both a mid-download error and a
200 response with an empty body, which is plausible for the very BoE CDN
that already misbehaves here.
"""
from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

USER_AGENT = "giltcurve-research/0.1"
DEFAULT_TIMEOUT = 120


def _urllib_download(url: str, dest: Path, timeout: int) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def _curl_download(url: str, dest: Path, timeout: int) -> None:
    proc = subprocess.run(
        ["curl", "-sSLf", "--max-time", str(timeout), "-A", USER_AGENT, "-o", str(dest), url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl exited {proc.returncode} for {url}: {proc.stderr.strip()}")


def fetch(url: str, dest: str | Path, *, force: bool = False, timeout: int = DEFAULT_TIMEOUT,
          max_age_days: float | None = None) -> Path:
    """Download ``url`` to ``dest`` (cached unless ``force``) and return its path.

    Returns the path rather than the bytes so callers that hand the file to
    ``zipfile`` or ``read_excel`` -- which is most of them, and the ones
    fetching the largest archives -- do not pay for a pointless full read of a
    file that was just written. Callers wanting the content call
    ``.read_bytes()`` / ``.read_text()``.

    ``max_age_days``, if given, treats a cached file older than that many
    days (by mtime) as stale and re-downloads it even though ``force`` is
    False. Every adaptor that caches a periodically-refreshed source (daily
    FRED/Bundesbank series, fortnightly BoE archives) has the same staleness
    problem, which is why this lives here rather than in one caller. The
    default of ``None`` preserves indefinite caching, so every existing
    caller is unaffected.
    """
    dest = Path(dest)
    if dest.exists() and not force:
        if max_age_days is None or (time.time() - dest.stat().st_mtime) / 86400 <= max_age_days:
            return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        try:
            _urllib_download(url, tmp, timeout)
        except Exception:
            _curl_download(url, tmp, timeout)
        if tmp.stat().st_size == 0:
            raise RuntimeError(f"downloaded 0 bytes for {url}")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    return dest
