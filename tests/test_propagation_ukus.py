"""The UK-US models: restriction tables, the risk-premium shock, outcomes and the panel."""
import numpy as np
import pandas as pd
import pytest

from giltcurve.propagation import ukus
from giltcurve.propagation.data import HoldoutSealedError
from giltcurve.propagation.identification import fixed_sigma, match_columns, sample_identified_set

# Model B columns: UK MP, UK macro, UK risk premium, US MP, US macro, global risk.
# Rows: UK 2y, UK 10y, UK equity, US equity, sterling, UK-US spread.
B_TRUE = np.array([
    [4.0, 3.0, 1.0, 0.5, 0.3, -1.0],
    [3.0, 2.5, 3.0, 1.5, 1.2, -1.5],
    [-0.6, 0.7, -0.3, -0.2, 0.3, -0.9],
    [-0.1, 0.2, 0.1, -0.6, 0.7, -0.8],
    [0.4, 0.3, -0.5, -0.3, -0.2, -0.3],
    [2.0, 1.5, 2.0, -1.0, -0.9, 0.8],
])


def test_textbook_columns_satisfy_exactly_their_own_shock():
    np.testing.assert_array_equal(ukus.restriction_b(B_TRUE.T), np.eye(6, dtype=bool))
    a_cols = np.delete(np.delete(B_TRUE, 0, axis=0), 2, axis=1)         # drop UK 2y and risk premium
    np.testing.assert_array_equal(ukus.restriction_a(a_cols.T), np.eye(5, dtype=bool))


@pytest.mark.parametrize("fn, n", [(ukus.restriction_a, 5), (ukus.restriction_b, 6)])
def test_restriction_sets_are_exclusive_up_to_sign(fn, n):
    cols = np.random.default_rng(0).standard_normal((300_000, n))
    assert (fn(cols) | fn(-cols)).sum(axis=1).max() == 1


def test_the_risk_premium_signature_is_not_representable_in_model_a():
    # Gilts up relative to Treasuries while sterling falls: no Model A shock fits it.
    col_a = np.array([3.0, -0.3, 0.1, -0.5, 2.0])
    assert not (ukus.restriction_a(col_a) | ukus.restriction_a(-col_a)).any()
    col_b = np.r_[1.0, col_a]
    assert ukus.restriction_b(col_b)[2]


def test_sampler_recovers_valid_model_b_decompositions():
    Sigma = B_TRUE @ B_TRUE.T
    ident = sample_identified_set(fixed_sigma(Sigma), 40, np.random.default_rng(1),
                                  restriction=ukus.restriction_b, rotations_per_draw=500)
    np.testing.assert_allclose(ident.B @ np.swapaxes(ident.B, 1, 2),
                               np.broadcast_to(Sigma, ident.B.shape), atol=1e-9)
    shares = ukus.origin_variance_shares(ukus.SPEC_B, ident)
    assert sum(shares["d_uk10"]["by_origin"].values()) == pytest.approx(1.0)
    idx, Bm = match_columns(B_TRUE[:, [5, 0, 3, 1, 4, 2]][None], ukus.restriction_b)
    np.testing.assert_allclose(Bm[0], B_TRUE)


def test_us10_impact_is_the_uk_rate_minus_the_spread():
    b = ukus.impact_on(ukus.SPEC_B, B_TRUE, "us10")
    np.testing.assert_allclose(b, B_TRUE[1] - B_TRUE[5])


def test_panel_is_sealed_and_consistent():
    d = pd.bdate_range("2025-12-26", periods=8)
    s = lambda v: pd.Series(v, index=d, dtype=float)
    args = (s([4.0, 4.1, 4.05, 4.2, 4.3, 4.1, 4.2, 4.4]), s([4.5, 4.6, 4.55, 4.7, 4.8, 4.6, 4.7, 4.9]),
            s([4.0, 4.1, 4.0, 4.2, 4.1, 4.0, 4.3, 4.4]), s(np.arange(8.0)),
            s([100, 101, 99, 100, 102, 101, 100, 99]), s([1.30, 1.31, 1.30, 1.32, 1.33, 1.32, 1.31, 1.30]))
    with pytest.raises(HoldoutSealedError):
        ukus.build_panel(*args, start="2025-12-01", end="2026-01-06")
    p = ukus.build_panel(*args, start="2025-12-01")
    assert p.index.max() < pd.Timestamp("2026-01-01")
    np.testing.assert_allclose(p["d_spread"], p["d_uk10"] - p["d_us10"])
