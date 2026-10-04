"""The cross-Atlantic (Brandt et al.) model: restrictions, data and the origin test."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation import brandt
from giltcurve.propagation.data import HoldoutSealedError
from giltcurve.propagation.identification import fixed_sigma, match_columns, sample_identified_set
from giltcurve.propagation.predictive import ols_nw  # noqa: F401  (shared inference)

# Columns: EA MP, EA macro, US MP, US macro, global risk.
# Rows: EA 10y, EA equity, US equity, euro, EA-US spread.
B_TRUE = np.array([
    [3.0, 2.0, 1.5, 1.0, -1.5],
    [-0.5, 0.8, -0.2, 0.3, -0.9],
    [-0.1, 0.2, -0.6, 0.7, -0.8],
    [0.4, 0.2, -0.3, -0.2, -0.3],
    [2.0, 1.2, -2.0, -1.5, 1.0],
])


def test_textbook_columns_satisfy_exactly_their_own_shock():
    sat = brandt.restriction_matrix(B_TRUE.T)
    np.testing.assert_array_equal(sat, np.eye(5, dtype=bool))


def test_the_five_restriction_sets_are_exclusive_up_to_sign():
    cols = np.random.default_rng(0).standard_normal((300_000, 5))
    both = brandt.restriction_matrix(cols) | brandt.restriction_matrix(-cols)
    assert both.sum(axis=1).max() == 1


def test_matching_and_sampling_use_the_brandt_table():
    scrambled = (B_TRUE * np.array([1, -1, 1, -1, -1]))[:, [4, 2, 0, 3, 1]]
    idx, Bm = match_columns(scrambled[None], brandt.restriction_matrix)
    assert list(idx) == [0]
    np.testing.assert_allclose(Bm[0], B_TRUE)
    Sigma = B_TRUE @ B_TRUE.T
    ident = sample_identified_set(fixed_sigma(Sigma), 50, np.random.default_rng(1),
                                  restriction=brandt.restriction_matrix, rotations_per_draw=500)
    np.testing.assert_allclose(ident.B @ np.swapaxes(ident.B, 1, 2),
                               np.broadcast_to(Sigma, ident.B.shape), atol=1e-9)
    sat = brandt.restriction_matrix(np.swapaxes(ident.B, 1, 2))
    assert sat[:, np.arange(5), np.arange(5)].all()


def test_euro_equity_splices_the_proxy_before_the_euro_stoxx_starts():
    d = pd.bdate_range("2007-03-26", periods=10)
    dax = pd.Series(np.exp(np.linspace(0, 0.09, 10)), index=d)
    cac = pd.Series(np.exp(np.linspace(0, 0.03, 10)), index=d)
    es = pd.Series(np.exp(np.linspace(0, 0.18, 6)), index=d[4:])
    lv = brandt.euro_equity_log_level(es, dax, cac)
    r = lv.diff()
    assert r.iloc[2] == pytest.approx(100 * (0.01 + 0.00333333) / 2, rel=1e-4)   # proxy average
    assert r.iloc[6] == pytest.approx(100 * 0.036, rel=1e-4)                      # Euro Stoxx


def _levels():
    d = pd.bdate_range("2025-12-26", periods=8)
    s = lambda vals: pd.Series(vals, index=d, dtype=float)
    return (s([2.5, 2.6, 2.55, 2.7, 2.8, 2.6, 2.7, 2.9]), s([4.0, 4.1, 4.0, 4.2, 4.1, 4.0, 4.3, 4.4]),
            s(np.arange(8.0)), s([100, 101, 99, 100, 102, 101, 100, 99]),
            s([1.10, 1.11, 1.10, 1.12, 1.13, 1.12, 1.11, 1.10]))


def test_panel_is_sealed_and_the_spread_is_the_difference_of_the_two_rates():
    ea, us, eq_ea, eq_us, fx = _levels()
    with pytest.raises(HoldoutSealedError):
        brandt.build_panel(ea, us, eq_ea, eq_us, fx, start="2025-12-01", end="2026-01-06")
    p = brandt.build_panel(ea, us, eq_ea, eq_us, fx, start="2025-12-01")
    assert p.index.max() < pd.Timestamp("2026-01-01")
    np.testing.assert_allclose(p["d_spread"], p["d_ea10"] - p["d_us10"])
    assert p.loc["2025-12-30", "d_fx"] == pytest.approx(100 * np.log(1.10 / 1.11))
    u = brandt.build_panel(ea, us, eq_ea, eq_us, fx, start="2025-12-01", end="2026-01-06",
                           unseal_holdout=True)
    assert u.index.max() > pd.Timestamp("2026-01-01")


def test_origin_test_detects_continuation_of_foreign_news():
    rng = np.random.default_rng(3)
    T = 20000
    eps = rng.standard_normal((T, 5))
    U = eps @ B_TRUE.T
    b = brandt.impact_on(B_TRUE, "ea10")
    c_f, c_g = brandt.origin_contributions(eps, b, "ea10")
    d_ea = U[:, 0].copy()
    d_ea[1:] += 0.3 * c_f[:-1]                     # US-origin moves in Bund yields continue
    lv = np.cumsum(d_ea)
    r = np.r_[lv[1:] - lv[:-1], np.nan]
    Z = rng.standard_normal((T, 2)) * 0.01
    out = brandt.origin_split_test(r, d_ea, c_f, c_g, Z, 1)
    assert out["kappa_foreign"] == pytest.approx(0.3, abs=0.05)
    assert out["p"] < 1e-6 and abs(out["t_global"]) < 3
