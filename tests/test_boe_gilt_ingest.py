"""Real-data parse checks for the BoE nominal gilt zero curve.

Network-dependent; auto-skip offline, mirroring tests/test_boe_ingest.py.
"""
import numpy as np
import pytest

from giltcurve.ingest import boe_gilt


def _online():
    try:
        boe_gilt.ensure_gilt_workbook()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _online(), reason="needs network for BoE data")


def test_gilt_panel_is_dated_and_decimal():
    panel = boe_gilt.load_gilt_panel()
    assert panel.index.is_monotonic_increasing
    assert panel.shape[1] >= 10
    vals = panel.dropna(how="all").to_numpy(float)
    finite = vals[np.isfinite(vals)]
    assert finite.min() > -0.02 and finite.max() < 0.25  # decimals


def test_gilt_panel_has_no_weekend_rows():
    panel = boe_gilt.load_gilt_panel()
    weekdays = panel.index.dayofweek
    assert (weekdays < 5).all()  # no Sat/Sun (non-trading days)
