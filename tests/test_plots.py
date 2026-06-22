"""Smoke tests for the plotting layer: figures render to non-empty PNGs."""
import datetime as dt

import matplotlib

matplotlib.use("Agg")

import pandas as pd

from giltcurve.viz.plots import plot_implied_path, plot_curve


def _sample_path():
    return pd.DataFrame(
        {
            "meeting": [None, dt.date(2026, 8, 6), dt.date(2026, 9, 17)],
            "window_start": [dt.date(2026, 6, 22), dt.date(2026, 8, 6), dt.date(2026, 9, 17)],
            "window_end": [dt.date(2026, 8, 6), dt.date(2026, 9, 17), dt.date(2026, 11, 5)],
            "implied_bank_rate": [0.0420, 0.0395, 0.0370],
            "cum_change_bp": [0.0, -25.0, -50.0],
        }
    )


def test_plot_implied_path_writes_png(tmp_path):
    out = tmp_path / "path.png"
    plot_implied_path(_sample_path(), dt.date(2026, 6, 22), out)
    assert out.exists() and out.stat().st_size > 1000


def test_plot_curve_writes_png(tmp_path):
    out = tmp_path / "curve.png"
    plot_curve(
        [1, 2, 5, 10], [0.040, 0.041, 0.042, 0.043], [0.040, 0.042, 0.043, 0.044],
        dt.date(2026, 6, 22), out,
    )
    assert out.exists() and out.stat().st_size > 1000
