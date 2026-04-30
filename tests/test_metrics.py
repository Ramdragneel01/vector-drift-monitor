import numpy as np
import pytest

from vector_drift_monitor.metrics import (
    centroid,
    centroid_shift,
    cosine_distance,
    jensen_shannon,
    ks_test_per_dim,
    mean_norm,
    mean_norm_shift,
)


def _rng(seed: int = 0):
    return np.random.default_rng(seed)


def test_centroid_basic():
    x = np.array([[1.0, 0.0], [3.0, 0.0]])
    np.testing.assert_allclose(centroid(x), [2.0, 0.0])


def test_cosine_distance_identity():
    a = np.array([1.0, 0.0])
    assert cosine_distance(a, a) == pytest.approx(0.0, abs=1e-9)


def test_cosine_distance_orthogonal():
    assert cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)


def test_cosine_distance_zero_vector():
    # Either side zero → max distance, never NaN.
    assert cosine_distance([0.0, 0.0], [1.0, 0.0]) == 1.0


def test_centroid_shift_smaller_for_same_distribution_than_translated():
    rng = _rng(1)
    a = rng.standard_normal((500, 16))
    b = rng.standard_normal((500, 16))
    c = rng.standard_normal((500, 16)) + 5.0
    same = centroid_shift(a, b)
    translated = centroid_shift(a, c)
    # Translated centroid distance must dominate the same-distribution case.
    assert translated > same
    assert translated > 0.5


def test_centroid_shift_large_when_translated():
    rng = _rng(2)
    a = rng.standard_normal((300, 16))
    b = rng.standard_normal((300, 16)) + 5.0
    assert centroid_shift(a, b) > 0.10


def test_mean_norm_and_shift():
    a = np.array([[3.0, 4.0]])  # norm 5
    b = np.array([[6.0, 8.0]])  # norm 10
    assert mean_norm(a) == pytest.approx(5.0)
    assert mean_norm_shift(a, b) == pytest.approx(1.0)


def test_mean_norm_shift_zero_baseline_handled():
    a = np.array([[0.0, 0.0]])
    b = np.array([[0.0, 0.0]])
    assert mean_norm_shift(a, b) == 0.0


def test_ks_test_detects_shift():
    rng = _rng(3)
    a = rng.standard_normal((400, 4))
    b = rng.standard_normal((400, 4)) + 1.0
    stat, pval = ks_test_per_dim(a, b)
    assert stat > 0.2 and pval < 0.01


def test_ks_test_no_shift_high_pvalue():
    rng = _rng(4)
    a = rng.standard_normal((400, 4))
    b = rng.standard_normal((400, 4))
    _, pval = ks_test_per_dim(a, b)
    assert pval > 0.001  # could be small by chance, but never tiny


def test_ks_test_dim_mismatch_raises():
    a = np.zeros((5, 3))
    b = np.zeros((5, 4))
    with pytest.raises(ValueError):
        ks_test_per_dim(a, b)


def test_jensen_shannon_zero_when_identical():
    rng = _rng(5)
    a = rng.standard_normal((200, 8))
    assert jensen_shannon(a, a) == pytest.approx(0.0, abs=1e-9)


def test_jensen_shannon_positive_when_scaled():
    rng = _rng(6)
    a = rng.standard_normal((200, 8))
    b = rng.standard_normal((200, 8)) * 4.0
    assert jensen_shannon(a, b) > 0.05


def test_empty_matrix_rejected():
    with pytest.raises(ValueError):
        centroid(np.zeros((0, 4)))
