"""Tests for premium/panel.py — downstream-ready decomposed panel + differentials."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.premium.panel import decomposed_panel, cross_currency_differentials


def _toy_decomposed(currency, base_rate, tp_slope, dates):
    """Build a decomposed-panel-shaped frame directly (no estimation needed)."""
    mats = [1.0, 2.0, 5.0, 10.0]
    rows = []
    for d in dates:
        for m in mats:
            er = base_rate
            tp = tp_slope * m
            rows.append({"date": d, "currency": currency, "maturity": m,
                         "observed": er + tp, "fitted": er + tp,
                         "expected_rate": er, "term_premium": tp})
    return pd.DataFrame(rows)


def test_decomposed_panel_concatenates_currencies():
    dates = pd.date_range("2020-01-31", periods=3, freq="ME")
    us = _toy_decomposed("USD", 0.02, 0.001, dates)
    gb = _toy_decomposed("GBP", 0.03, 0.0008, dates)
    panel = decomposed_panel([us, gb])
    assert set(panel["currency"]) == {"USD", "GBP"}
    assert list(panel.columns) == [
        "date", "currency", "maturity", "observed", "fitted",
        "expected_rate", "term_premium",
    ]


def test_cross_currency_differentials_vs_usd():
    dates = pd.date_range("2020-01-31", periods=2, freq="ME")
    us = _toy_decomposed("USD", 0.02, 0.001, dates)
    gb = _toy_decomposed("GBP", 0.03, 0.0008, dates)
    panel = decomposed_panel([us, gb])
    diff = cross_currency_differentials(panel, tenor=10.0, base="USD")
    # GBP 10y: exp-rate diff = 0.03-0.02 = 0.01; tp diff = (0.0008-0.001)*10 = -0.002
    g = diff[diff["currency"] == "GBP"].iloc[0]
    assert abs(g["exp_rate_diff"] - 0.01) < 1e-12
    assert abs(g["term_premium_diff"] - (-0.002)) < 1e-12
    # USD vs itself is dropped (base)
    assert "USD" not in set(diff["currency"])


def test_cross_currency_differentials_missing_base_raises():
    dates = pd.date_range("2020-01-31", periods=2, freq="ME")
    panel = decomposed_panel([_toy_decomposed("GBP", 0.03, 0.0008, dates)])
    with pytest.raises(ValueError):
        cross_currency_differentials(panel, tenor=10.0, base="USD")


def test_cross_currency_differentials_missing_tenor_raises():
    dates = pd.date_range("2020-01-31", periods=2, freq="ME")
    panel = decomposed_panel([
        _toy_decomposed("USD", 0.02, 0.001, dates),
        _toy_decomposed("GBP", 0.03, 0.0008, dates),
    ])
    with pytest.raises(ValueError):  # 7y is not in the toy maturities [1,2,5,10]
        cross_currency_differentials(panel, tenor=7.0, base="USD")


def test_cross_currency_differentials_inner_joins_dates():
    us = _toy_decomposed("USD", 0.02, 0.001, pd.date_range("2020-01-31", periods=3, freq="ME"))
    gb = _toy_decomposed("GBP", 0.03, 0.0008, pd.date_range("2020-02-29", periods=3, freq="ME"))
    diff = cross_currency_differentials(decomposed_panel([us, gb]), tenor=10.0, base="USD")
    gb_dates = set(diff[diff["currency"] == "GBP"]["date"])
    assert len(gb_dates) == 2  # only the 2 overlapping months survive the inner join
