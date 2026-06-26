"""Network-free unit test for load_gilt_history's vintage-priority dedupe."""
import datetime as dt

import pandas as pd

from giltcurve.ingest import boe_gilt


def _write_gilt_xlsx(path, sheet_name, dates, mats, values_pct):
    # Matches parse_ois_sheet's expected layout: a 'years:' header row
    # (col A label, maturities in cols B+), then date rows (values in percent).
    rows = [["years:"] + list(mats)]
    for d, vals in zip(dates, values_pct):
        rows.append([d] + list(vals))
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name=sheet_name, header=False, index=False)


def test_load_gilt_history_prefers_current_month_on_overlap(tmp_path):
    mats = [1, 2, 5, 10]
    overlap = dt.datetime(2026, 6, 1)
    # stale rolling-history vintage: 5.00% at the overlap date
    _write_gilt_xlsx(
        tmp_path / "GLC Nominal daily data_2025 to present.xlsx", "4. spot curve",
        [dt.datetime(2026, 5, 1), overlap], mats,
        [[5, 5, 5, 5], [5, 5, 5, 5]],
    )
    # fresh current-month vintage: 4.00% at the same overlap date
    _write_gilt_xlsx(
        tmp_path / "GLC Nominal daily data current month.xlsx", "4. spot curve",
        [overlap, dt.datetime(2026, 6, 2)], mats,
        [[4, 4, 4, 4], [4, 4, 4, 4]],
    )
    panel = boe_gilt.load_gilt_history(data_dir=tmp_path)
    # parse_ois_sheet divides percent by 100; fresh value (0.04) must win
    assert panel.loc[pd.Timestamp(overlap), 1.0] == 0.04
