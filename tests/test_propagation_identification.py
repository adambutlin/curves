"""Sign restrictions: shock definitions, exclusivity, matching and the sampler."""
import numpy as np
import pytest

from giltcurve.propagation.identification import (
    SHOCKS, fixed_sigma, haar_rotations, match_columns, restriction_matrix,
    sample_identified_set,
)

# A textbook impact matrix (rows dy2, dy5, dy10, req; columns in SHOCKS order).
B_TRUE = np.array([
    [3.0, 4.0, 1.0, -1.0],
    [3.0, 3.0, 2.0, -2.0],
    [2.0, 2.0, 3.0, -3.0],
    [0.8, -0.4, -0.6, -0.7],
])


def test_each_textbook_column_satisfies_exactly_its_own_shock():
    sat = restriction_matrix(B_TRUE.T)
    np.testing.assert_array_equal(sat, np.eye(4, dtype=bool))
    assert not restriction_matrix(np.array([1.0, -1.0, 1.0, 1.0])).any()


def test_restriction_sets_are_mutually_exclusive_up_to_sign():
    cols = np.random.default_rng(0).standard_normal((200_000, 4))
    both = restriction_matrix(cols) | restriction_matrix(-cols)
    assert both.sum(axis=1).max() == 1


def test_haar_draws_are_orthogonal():
    Q = haar_rotations(4, 1000, np.random.default_rng(1))
    np.testing.assert_allclose(Q @ np.swapaxes(Q, 1, 2), np.broadcast_to(np.eye(4), Q.shape), atol=1e-12)
    assert np.abs(Q.mean(axis=0)).max() < 0.1


def test_matching_undoes_any_column_permutation_and_sign_flip():
    scrambled = (B_TRUE * np.array([1, -1, -1, 1]))[:, [2, 0, 3, 1]]
    idx, Bm = match_columns(scrambled[None])
    assert list(idx) == [0]
    np.testing.assert_allclose(Bm[0], B_TRUE)


def test_sampler_returns_valid_decompositions_of_sigma():
    Sigma = B_TRUE @ B_TRUE.T
    ident = sample_identified_set(fixed_sigma(Sigma), 300, np.random.default_rng(2))
    assert ident.B.shape == (300, 4, 4)
    np.testing.assert_allclose(ident.B @ np.swapaxes(ident.B, 1, 2),
                               np.broadcast_to(Sigma, ident.B.shape), atol=1e-9)
    sat = restriction_matrix(np.swapaxes(ident.B, 1, 2))
    assert sat[:, np.arange(4), np.arange(4)].all()
    shares = ident.variance_shares()
    np.testing.assert_allclose(shares.sum(axis=2), 1.0, atol=1e-9)
    assert 0 < ident.acceptance_rate < 1
    assert 0 <= ident.median_target() < 300


def test_shocks_invert_the_impact_matrix():
    Sigma = B_TRUE @ B_TRUE.T
    ident = sample_identified_set(fixed_sigma(Sigma), 10, np.random.default_rng(3))
    eps = np.random.default_rng(4).standard_normal((50, 4))
    U = eps @ ident.B[0].T
    np.testing.assert_allclose(ident.shocks(U, 0), eps, atol=1e-10)
    assert len(SHOCKS) == 4
