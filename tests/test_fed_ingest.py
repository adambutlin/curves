"""Real-data parse checks for the US anchor (GSW + NY Fed ACM).

Network-dependent; auto-skip when offline, mirroring tests/test_boe_ingest.py.
"""
import numpy as np
import pytest

from giltcurve.ingest import fed


def _online():
    try:
        fed.download_gsw(force=False)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _online(), reason="needs network for Fed data")


def test_gsw_panel_shape_and_units():
    panel = fed.load_gsw_panel()
    assert panel.shape[1] >= 10
    assert panel.columns.min() == 1.0
    vals = panel.dropna(how="all").to_numpy(float)
    finite = vals[np.isfinite(vals)]
    assert finite.min() > -0.02 and finite.max() < 0.25  # decimals, not percent


def test_acm_series_has_10y_term_premium():
    acm = fed.load_nyfed_acm()
    tp10 = fed.nyfed_term_premium(acm, tenor=10.0)
    assert tp10.notna().sum() > 200  # decades of monthly data
