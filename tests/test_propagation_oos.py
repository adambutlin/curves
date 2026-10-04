"""Pseudo out-of-sample: real-time discipline and the Clark-West statistic."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation.oos import clark_west, pseudo_oos, summarise


def _panel(T=1600, seed=0):
    rng = np.random.default_rng(seed)
    B = np.array([[3.0, 4.0, 1.0, -1.0], [3.0, 3.0, 2.0, -2.0],
                  [2.0, 2.0, 3.0, -3.0], [0.8, -0.4, -0.6, -0.7]])
    dy = rng.standard_normal((T, 4)) @ B.T
    idx = pd.bdate_range("2017-01-02", periods=T)
    lv = 2.0 + np.cumsum(dy[:, :3], axis=0) / 100.0
    return pd.DataFrame({"y2": lv[:, 0], "y5": lv[:, 1], "y10": lv[:, 2], "dy2": dy[:, 0],
                         "dy5": dy[:, 1], "dy10": dy[:, 2], "req": dy[:, 3]}, index=idx)


def _run(panel):
    return pseudo_oos(panel, years=[2020, 2021], n_draws=5, horizons=(1, 5), outcomes=("y10",))


def test_forecasts_made_before_a_data_change_do_not_move():
    panel = _panel()
    base = _run(panel)
    cut = pd.Timestamp("2021-06-01")
    altered = panel.copy()
    later = altered.index >= cut
    altered.loc[later, ["dy2", "dy5", "dy10", "req"]] *= 5.0       # rewrite the future
    alt = _run(altered)
    before = (base["date"] < cut - pd.Timedelta(days=10)).to_numpy()
    for m in ("m1", "m2", "m3", "m4"):
        np.testing.assert_allclose(alt.loc[before, m].to_numpy(), base.loc[before, m].to_numpy())


def test_every_forecast_year_is_scored_only_on_its_own_days():
    fc = _run(_panel())
    assert set(fc["year"]) == {2020, 2021}
    assert (fc["date"].dt.year == fc["year"]).all()
    s = summarise(fc, periods={"all": (2020, 2021)})
    assert set(s["h"]) == {1, 5}
    assert (s["r2_m4_vs_m2"] < 0.05).all()          # nothing to find in white noise


def test_clark_west_detects_a_genuinely_better_nested_forecast():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(5000)
    y = 0.3 * x + rng.standard_normal(5000)
    t_good, p_good = clark_west(y, np.zeros(5000), 0.3 * x, lags=1)
    assert t_good > 5 and p_good < 1e-6
    t_bad, p_bad = clark_west(y, np.zeros(5000), 0.3 * rng.standard_normal(5000), lags=1)
    assert p_bad > 0.05
