"""Tests for ingest/_http.py — cached fetch with a curl fallback."""
import urllib.error

import pytest

from giltcurve.ingest import _http


def test_returns_cached_path_without_calling_network(tmp_path, monkeypatch):
    dest = tmp_path / "cached.bin"
    dest.write_bytes(b"already here")

    def _boom(*args, **kwargs):
        raise AssertionError("network must not be touched when the cache is warm")

    monkeypatch.setattr(_http, "_urllib_download", _boom)
    monkeypatch.setattr(_http, "_curl_download", _boom)
    result = _http.fetch("https://example.invalid/x.bin", dest)
    assert result == dest
    assert result.read_bytes() == b"already here"


def test_force_refetches_even_when_cached(tmp_path, monkeypatch):
    dest = tmp_path / "cached.bin"
    dest.write_bytes(b"stale")
    monkeypatch.setattr(_http, "_urllib_download", lambda url, d, t: d.write_bytes(b"fresh"))
    result = _http.fetch("https://example.invalid/x.bin", dest, force=True)
    assert result.read_bytes() == b"fresh"


def test_falls_back_to_curl_when_urllib_fails(tmp_path, monkeypatch):
    dest = tmp_path / "out.bin"

    def _fail(url, d, timeout):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(_http, "_urllib_download", _fail)
    monkeypatch.setattr(_http, "_curl_download", lambda url, d, t: d.write_bytes(b"via curl"))
    result = _http.fetch("https://example.invalid/x.bin", dest)
    assert result.read_bytes() == b"via curl"


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
    tmp = dest.with_suffix(dest.suffix + ".part")
    # Recorded rather than asserted inline: an inline assert here would raise
    # AssertionError from *inside* _urllib_download, which fetch()'s own
    # broad `except Exception` would swallow and mask as the curl fallback's
    # RuntimeError, letting `pytest.raises(RuntimeError)` pass either way.
    dest_existed_during_write = []

    def _half_written(url, d, timeout):
        d.write_bytes(b"partial")
        dest_existed_during_write.append(dest.exists())
        raise urllib.error.URLError("connection reset")

    def _curl_fail(url, d, timeout):
        raise RuntimeError("curl exited 7")

    monkeypatch.setattr(_http, "_urllib_download", _half_written)
    monkeypatch.setattr(_http, "_curl_download", _curl_fail)
    with pytest.raises(RuntimeError):
        _http.fetch("https://example.invalid/x.bin", dest)
    assert dest_existed_during_write == [False]  # pins the temp-file indirection: d is not dest
    assert not dest.exists()
    assert not tmp.exists()  # pins the unlink of the temp file on failure


def test_creates_missing_parent_directories(tmp_path, monkeypatch):
    dest = tmp_path / "nested" / "does" / "not" / "exist" / "out.bin"
    monkeypatch.setattr(_http, "_urllib_download", lambda url, d, t: d.write_bytes(b"data"))
    result = _http.fetch("https://example.invalid/x.bin", dest)
    assert result.read_bytes() == b"data"


def test_empty_body_download_is_not_cached(tmp_path, monkeypatch):
    dest = tmp_path / "out.bin"

    def _empty(url, d, timeout):
        d.write_bytes(b"")

    monkeypatch.setattr(_http, "_urllib_download", _empty)
    monkeypatch.setattr(_http, "_curl_download", _empty)
    with pytest.raises(RuntimeError, match="0 bytes.*https://example.invalid/x.bin"):
        _http.fetch("https://example.invalid/x.bin", dest)
    assert not dest.exists()


def test_urllib_download_fetches_a_real_file_url(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"real urllib content")
    dest = tmp_path / "dest.bin"
    _http._urllib_download(src.as_uri(), dest, 10)
    assert dest.read_bytes() == b"real urllib content"


def test_curl_download_fetches_a_real_file_url(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"real curl content")
    dest = tmp_path / "dest.bin"
    _http._curl_download(src.as_uri(), dest, 10)
    assert dest.read_bytes() == b"real curl content"


def test_curl_download_raises_runtime_error_for_missing_file(tmp_path):
    dest = tmp_path / "dest.bin"
    missing = (tmp_path / "does-not-exist.bin").as_uri()
    with pytest.raises(RuntimeError, match="curl exited"):
        _http._curl_download(missing, dest, 10)
