"""Tests for the BoE OIS-curve ingester.

A synthetic workbook mirrors the exact BoE layout (title / 'Maturity' /
'months:' / 'years:' / '#VALUE!' / date-keyed data rows) so the parser is
covered offline and deterministically. A separate, skip-unless-present
integration check validates against the real downloaded file: a curve built
from BoE's published spot rates must reproduce BoE's published instantaneous
forward curve to within ~2bp -- the empirical proof that our continuous
compounding convention matches theirs.
"""
import datetime as dt
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from giltcurve.ingest.boe import (
    parse_ois_sheet,
    latest_spot_curve,
    build_curve_from_spot,
)

REAL_OIS = Path("data/raw/OIS daily data current month.xlsx")


def _write_synthetic_ois(path, sheet="3. spot, short end"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append([None, "UK OIS spot curve, short end"])
    ws.append(["Maturity"])
    ws.append(["months:", 6, 12, 18])
    ws.append(["years:", 0.5, 1.0, 1.5])
    ws.append(["#VALUE!"])
    ws.append([dt.datetime(2026, 6, 1), 3.88, 4.05, 4.14])
    ws.append([dt.datetime(2026, 6, 2), 3.90, 4.07, 4.18])
    wb.save(path)


def test_parse_ois_sheet_shape_and_units(tmp_path):
    f = tmp_path / "ois.xlsx"
    _write_synthetic_ois(f)
    df = parse_ois_sheet(f, "3. spot, short end")
    assert list(df.columns) == [0.5, 1.0, 1.5]
    assert len(df) == 2
    # percent -> decimal
    assert df.iloc[0, 1] == pytest.approx(0.0405)
    assert df.index[-1].date() == dt.date(2026, 6, 2)


def test_latest_spot_curve_picks_last_row(tmp_path):
    f = tmp_path / "ois.xlsx"
    _write_synthetic_ois(f)
    df = parse_ois_sheet(f, "3. spot, short end")
    asof, mats, spots = latest_spot_curve(df)
    assert asof == dt.date(2026, 6, 2)
    np.testing.assert_allclose(mats, [0.5, 1.0, 1.5])
    np.testing.assert_allclose(spots, [0.039, 0.0407, 0.0418])


def test_build_curve_reprices_input_spot(tmp_path):
    f = tmp_path / "ois.xlsx"
    _write_synthetic_ois(f)
    df = parse_ois_sheet(f, "3. spot, short end")
    asof, mats, spots = latest_spot_curve(df)
    curve = build_curve_from_spot(mats, spots, asof)
    np.testing.assert_allclose(curve.zero(mats), spots, atol=1e-12)


@pytest.mark.skipif(not REAL_OIS.exists(), reason="real BoE OIS workbook not downloaded")
def test_curve_matches_boe_published_forwards():
    spot = parse_ois_sheet(REAL_OIS, "3. spot, short end")
    fwd = parse_ois_sheet(REAL_OIS, "1. fwds, short end")
    asof, mats, spots = latest_spot_curve(spot)
    curve = build_curve_from_spot(mats, spots, asof)
    boe_fwd = fwd.loc[fwd.index[-1]].dropna()
    ours = curve.inst_forward(boe_fwd.index.to_numpy(float))
    rmse_bp = np.sqrt(np.nanmean((ours - boe_fwd.to_numpy(float)) ** 2)) * 1e4
    assert rmse_bp < 2.0
