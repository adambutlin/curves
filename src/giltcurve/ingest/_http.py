"""Cached HTTP fetch with a curl fallback.

Python's ``urllib`` times out connecting to the Bank of England CDN in some
sandboxed environments while ``curl`` succeeds on the identical URL (verified
2026-08-20). Every ingest adaptor therefore goes through :func:`fetch`, which
tries ``urllib`` first and falls back to the ``curl`` binary.

Downloads are written to a temporary sibling and moved into place only on
success, so a failed fetch never leaves a truncated file that a later cached
read would happily return.
"""
from __future__ import annotations

import subprocess
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


def fetch(url: str, dest, *, force: bool = False, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Download ``url`` to ``dest`` (cached unless ``force``) and return its bytes."""
    dest = Path(dest)
    if dest.exists() and not force:
        return dest.read_bytes()

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        try:
            _urllib_download(url, tmp, timeout)
        except Exception:
            _curl_download(url, tmp, timeout)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    return dest.read_bytes()
