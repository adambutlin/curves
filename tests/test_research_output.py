"""Consistency of the published tables behind the 2026 Treasury selloff note (output/data/)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1] / "output" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "decomposition_2026.csv").exists(), reason="tables not built")


def test_median_target_contributions_add_up_to_the_actual_change():
    d = pd.read_csv(DATA / "decomposition_2026.csv")
    parts = d[["us_news_mt", "global_risk_mt", "euro_area_mt", "unspanned_mt"]].sum(axis=1)
    assert np.allclose(parts, d["actual_bp"], atol=0.01)
    assert np.allclose(d["us_macro_mt"] + d["us_monetary_mt"], d["us_news_mt"], atol=0.01)


def test_daily_10y_table_ends_at_the_window_totals():
    daily = pd.read_csv(DATA / "us10y_daily_cumulative_2026.csv")
    full = pd.read_csv(DATA / "decomposition_2026.csv").query("maturity == '10y'").iloc[0]
    assert daily["date"].iloc[0] == "2025-12-30" and daily.iloc[0, 1:].abs().max() == 0
    end = daily.iloc[-1]
    for col in ("us_news", "global_risk", "euro_area", "unspanned"):
        assert end[col] == pytest.approx(full[f"{col}_mt"], abs=0.01)
    assert end["actual"] == pytest.approx(full["actual_bp"], abs=0.01)
    assert (daily["us_news_p05"] <= daily["us_news_p95"] + 1e-9).all()


def test_probabilities_are_shares_and_origins_partition_the_draws():
    d = pd.read_csv(DATA / "decomposition_2026.csv")
    p = d[["p_us_largest", "p_global_largest", "p_euro_largest"]]
    assert ((p >= 0) & (p <= 1)).all().all()
    assert np.allclose(p.sum(axis=1), 1.0)


def test_research_page_has_every_number_filled():
    page = (DATA.parent / "2026_treasury_selloff.html").read_text(encoding="utf-8")
    assert "%%" not in page
    numbers = json.loads((DATA / "headline_numbers.json").read_text())
    assert numbers["10y_actual"] in page and numbers["2y_un_rng"] in page
