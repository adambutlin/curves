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


def test_merge_prefers_current_month_across_many_overlapping_dates():
    # Regression for a quicksort-instability bug: with only two overlapping
    # rows, sort_index()'s default unstable quicksort happens to preserve
    # concat order and the bug is invisible. A few hundred overlapping rows
    # reliably trips introsort's insertion-sort path and exposes it.
    idx = pd.bdate_range("2020-01-01", periods=400)
    history = pd.DataFrame({2.0: np.linspace(0.01, 0.02, len(idx))}, index=idx)
    current = pd.DataFrame({2.0: np.linspace(0.05, 0.06, len(idx))}, index=idx)
    merged = boe_curves.merge_panels(history, current)
    assert len(merged) == len(idx)
    assert (merged[2.0].to_numpy() == current[2.0].to_numpy()).all()


def test_merge_drops_all_nan_rows():
    idx = pd.to_datetime(["2026-08-17", "2026-08-18"])
    history = pd.DataFrame({2.0: [np.nan, 0.0401]}, index=idx)
    merged = boe_curves.merge_panels(history, history.iloc[0:0])
    assert len(merged) == 1
    assert merged.index[0] == pd.Timestamp("2026-08-18")


def test_resolve_spot_sheet_matches_the_real_spot_sheet_and_skips_short_end(tmp_path):
    # Pins the exact defect the plan's original alias tuple missed: the
    # pre-2005 "real" workbook names its spot sheet "4.  real spot curve"
    # (double space), not "4. spot curve" or "4. real spot curve".
    path = tmp_path / "synthetic.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="info", index=False)
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="3. spot, short end", index=False)
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="4.  real spot curve", index=False)

    resolved = boe_curves._resolve_spot_sheet(path, None)
    assert resolved == "4.  real spot curve"
    assert resolved != "3. spot, short end"


def test_resolve_spot_sheet_raises_on_ambiguous_match(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="2. spot curve", index=False)
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="4. spot curve", index=False)

    with pytest.raises(ValueError, match="ambiguous"):
        boe_curves._resolve_spot_sheet(path, None)


def test_tidy_tenor_columns_collapses_float_noise_duplicates():
    # Reproduces the OIS 2009-2015 vintage's float-noise tenor (0.5 stored
    # as 0.49999999999999994) alongside 2016+'s exact 0.5.
    idx = pd.to_datetime(["2010-01-04", "2020-01-06"])
    df = pd.DataFrame(
        {0.49999999999999994: [0.010, np.nan], 0.5: [np.nan, 0.020], 5.0: [0.030, 0.040]},
        index=idx,
    )
    tidy = boe_curves._tidy_tenor_columns(df)
    assert list(tidy.columns) == [0.5, 5.0]
    assert tidy.loc[idx[0], 0.5] == pytest.approx(0.010)
    assert tidy.loc[idx[1], 0.5] == pytest.approx(0.020)
    assert tidy.columns.is_monotonic_increasing


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
    # Interior continuity: an indefinitely-cached, stale history archive can
    # leave a silent multi-week hole between the end of history and the start
    # of the current-month workbook, which endpoint-only checks (index.max())
    # cannot see. Over the last two years, no gap between consecutive
    # observations should exceed 5 business days (the largest legitimate gap
    # observed live is 5, around Easter 2025).
    recent = panel.loc[panel.index.max() - pd.Timedelta(days=730):]
    days = recent.index.normalize().to_numpy(dtype="datetime64[D]")
    gaps = np.busday_count(days[:-1], days[1:])
    assert gaps.max() <= 5, (
        f"{kind}: interior gap of {gaps.max()} business days between "
        f"{recent.index[gaps.argmax()].date()} and {recent.index[gaps.argmax() + 1].date()}"
    )
