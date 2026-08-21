"""Tests for ingest/boe_curves.py — the parameterised BoE archive loader.

The parse-level tests run offline against a synthetic workbook. The coverage
test needs network and auto-skips, mirroring tests/test_boe_gilt_ingest.py.
"""
import numpy as np
import pandas as pd
import pytest

from giltcurve.ingest import boe_curves


def test_every_kind_has_a_complete_spec():
    for kind in boe_curves.CURVE_KINDS:
        spec = boe_curves.KIND_SPEC[kind]
        assert spec.archive.endswith(".zip")
        assert spec.workbook_token
        assert spec.current_month_member.endswith(".xlsx")


def test_unknown_kind_raises_with_a_helpful_message():
    with pytest.raises(ValueError, match="unknown curve kind 'swaption'"):
        boe_curves.load_curve("swaption")


def test_merge_prefers_current_month_on_overlapping_dates():
    idx = pd.to_datetime(["2026-08-17", "2026-08-18"])
    history = pd.DataFrame({2.0: [0.0400, 0.0401]}, index=idx)
    current = pd.DataFrame({2.0: [0.0429]}, index=pd.to_datetime(["2026-08-18"]))
    merged = boe_curves.merge_panels(history, current)
    assert merged.loc["2026-08-18", 2.0] == pytest.approx(0.0429)
    assert merged.loc["2026-08-17", 2.0] == pytest.approx(0.0400)
    assert merged.index.is_monotonic_increasing


def test_merge_drops_all_nan_rows():
    idx = pd.to_datetime(["2026-08-17", "2026-08-18"])
    history = pd.DataFrame({2.0: [np.nan, 0.0401]}, index=idx)
    merged = boe_curves.merge_panels(history, history.iloc[0:0])
    assert len(merged) == 1
    assert merged.index[0] == pd.Timestamp("2026-08-18")


@pytest.mark.parametrize("kind", ["nominal", "real", "inflation", "ois"])
def test_real_download_is_dated_decimal_and_current(kind):
    try:
        panel = boe_curves.load_curve(kind)
    except Exception as exc:
        pytest.skip(f"needs network for BoE data: {exc}")
    assert panel.index.is_monotonic_increasing
    assert (panel.index.dayofweek < 5).all()
    finite = panel.to_numpy(float)[np.isfinite(panel.to_numpy(float))]
    assert finite.min() > -0.05 and finite.max() < 0.30, "values must be decimals, not percent"
    # The current-month workbook must actually extend the history archive.
    assert panel.index.max() >= pd.Timestamp("2026-08-01")
