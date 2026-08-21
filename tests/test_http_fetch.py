"""Tests for ingest/_http.py — cached fetch with a curl fallback."""
import urllib.error

import pytest

from giltcurve.ingest import _http


def test_returns_cached_bytes_without_calling_network(tmp_path, monkeypatch):
    dest = tmp_path / "cached.bin"
    dest.write_bytes(b"already here")

    def _boom(*args, **kwargs):
        raise AssertionError("network must not be touched when the cache is warm")

    monkeypatch.setattr(_http, "_urllib_download", _boom)
    monkeypatch.setattr(_http, "_curl_download", _boom)
    assert _http.fetch("https://example.invalid/x.bin", dest) == b"already here"


def test_force_refetches_even_when_cached(tmp_path, monkeypatch):
    dest = tmp_path / "cached.bin"
    dest.write_bytes(b"stale")
    monkeypatch.setattr(_http, "_urllib_download", lambda url, d, t: d.write_bytes(b"fresh"))
    assert _http.fetch("https://example.invalid/x.bin", dest, force=True) == b"fresh"


def test_falls_back_to_curl_when_urllib_fails(tmp_path, monkeypatch):
    dest = tmp_path / "out.bin"

    def _fail(url, d, timeout):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(_http, "_urllib_download", _fail)
    monkeypatch.setattr(_http, "_curl_download", lambda url, d, t: d.write_bytes(b"via curl"))
    assert _http.fetch("https://example.invalid/x.bin", dest) == b"via curl"


def test_raises_when_both_transports_fail(tmp_path, monkeypatch):
    dest = tmp_path / "out.bin"

    def _fail(url, d, timeout):
        raise urllib.error.URLError("timed out")

    def _curl_fail(url, d, timeout):
        raise RuntimeError("curl exited 7")

    monkeypatch.setattr(_http, "_urllib_download", _fail)
    monkeypatch.setattr(_http, "_curl_download", _curl_fail)
    with pytest.raises(RuntimeError, match="curl exited 7"):
        _http.fetch("https://example.invalid/x.bin", dest)


def test_partial_download_is_not_left_behind(tmp_path, monkeypatch):
    dest = tmp_path / "out.bin"

    def _half_written(url, d, timeout):
        d.write_bytes(b"partial")
        raise urllib.error.URLError("connection reset")

    def _curl_fail(url, d, timeout):
        raise RuntimeError("curl exited 7")

    monkeypatch.setattr(_http, "_urllib_download", _half_written)
    monkeypatch.setattr(_http, "_curl_download", _curl_fail)
    with pytest.raises(RuntimeError):
        _http.fetch("https://example.invalid/x.bin", dest)
    assert not dest.exists()
