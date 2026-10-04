"""The estimation panel: alignment, units and the sealed 2026 holdout."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation.data import (
    HOLDOUT_START, HoldoutSealedError, build_panel, seal,
)


def _toy():
    dates = pd.to_datetime(["2025-12-29", "2025-12-30", "2025-12-31", "2026-01-02", "2026-01-05"])
    yields = pd.DataFrame({"y2": [4.00, 4.10, 4.05, 4.50, 4.60],
                           "y5": [4.20, 4.25, 4.20, 4.70, 4.80],
                           "y10": [4.50, 4.52, 4.49, 5.00, 5.10]}, index=dates)
    eq = pd.Series([1.0, -1.0, 0.5, 3.0, 3.0], index=dates)
    return yields, eq


def test_seal_drops_every_holdout_observation():
    yields, _ = _toy()
    sealed = seal(yields)
    assert sealed.index.max() < HOLDOUT_START
    assert len(seal(yields, unseal_holdout=True)) == len(yields)


def test_requesting_a_holdout_end_date_without_unsealing_raises():
    yields, eq = _toy()
    with pytest.raises(HoldoutSealedError):
        build_panel(yields, eq, start="2025-12-01", end="2026-01-05")


def test_sealed_panel_never_contains_2026_even_if_inputs_do():
    yields, eq = _toy()
    panel = build_panel(yields, eq, start="2025-12-01")
    assert panel.index.max() < HOLDOUT_START
    # Changes in basis points, equity as a log return in percent.
    assert panel.loc["2025-12-30", "dy2"] == pytest.approx(10.0)
    assert panel.loc["2025-12-31", "dy10"] == pytest.approx(-3.0)
    assert panel.loc["2025-12-30", "req"] == pytest.approx(100 * np.log(0.99))


def test_one_market_holiday_folds_into_the_next_common_day():
    dates = pd.to_datetime(["2024-10-11", "2024-10-14", "2024-10-15"])  # 14 Oct: bond market shut
    yields = pd.DataFrame({"y2": [4.0, np.nan, 4.1], "y5": [4.1, np.nan, 4.2],
                           "y10": [4.2, np.nan, 4.3]}, index=dates)
    eq = pd.Series([0.0, 1.0, 1.0], index=dates)
    panel = build_panel(yields.dropna(), eq, start="2024-10-01")
    assert list(panel.index) == [pd.Timestamp("2024-10-15")]
    # Two equity days compound into one return; one yield change over the same span.
    assert panel["req"].iloc[0] == pytest.approx(200 * np.log(1.01))
    assert panel["dy10"].iloc[0] == pytest.approx(10.0)
