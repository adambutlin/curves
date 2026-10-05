"""Synchronised euro-area data: futures roll calendar, roll adjustment, OIS splice."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.ingest.lseg import roll_adjusted_log_level, roll_days, third_friday
from giltcurve.propagation.brandt import spliced_ois


def test_roll_calendar_matches_the_switch_days_refinitiv_reports():
    days = pd.bdate_range("2021-07-01", "2022-12-31")
    fesx = [d for d in roll_days(days, "fesx") if d >= pd.Timestamp("2021-07-23")]
    fgbl = [d for d in roll_days(days, "fgbl") if d >= pd.Timestamp("2021-07-23")]
    assert [str(d.date()) for d in fesx[:4]] == ["2021-09-20", "2021-12-20", "2022-03-21", "2022-06-20"]
    assert [str(d.date()) for d in fgbl[:4]] == ["2021-09-09", "2021-12-09", "2022-03-09", "2022-06-09"]
    assert third_friday(2026, 3) == pd.Timestamp("2026-03-20")


def test_roll_adjustment_removes_the_contract_switch_jump():
    days = pd.bdate_range("2021-09-13", "2021-09-24")
    front_old = pd.Series(100.0, index=days)                 # September contract, flat
    next_c = pd.Series(98.0, index=days)                      # December contract, 2 points lower
    c1 = front_old.where(days < pd.Timestamp("2021-09-20"), next_c)   # switch after the 17th
    c2 = next_c
    lv = roll_adjusted_log_level(c1, c2, "fesx")
    assert np.abs(lv.diff().dropna()).max() == pytest.approx(0.0, abs=1e-12)
    raw = np.log(c1).diff().abs().max() * 100
    assert raw > 2.0                                          # the unadjusted series jumps


def test_ois_splice_is_continuous_and_keeps_estr_changes():
    d = pd.bdate_range("2019-12-26", periods=8)
    eonia = pd.Series([0.10, 0.12, 0.11, 0.13, 0.15, 0.16, 0.14, 0.15], index=d)
    estr = eonia - 0.085 + np.r_[0, 0, 0, 0, 0.01, 0.02, 0.0, 0.03]
    s = spliced_ois(eonia, estr, switch=pd.Timestamp("2020-01-02"))
    i = list(d).index(pd.Timestamp("2020-01-02"))
    np.testing.assert_allclose(s.diff().iloc[i + 1:], estr.diff().iloc[i + 1:])
    assert s.iloc[i] - s.iloc[i - 1] == pytest.approx(estr.iloc[i] - estr.iloc[i - 1])
