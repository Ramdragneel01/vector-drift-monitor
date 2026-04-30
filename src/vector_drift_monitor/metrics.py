"""Pure-function drift metrics over numpy embedding matrices.

All inputs are expected as 2-D arrays of shape (n_vectors, dim).
Functions are deterministic, side-effect free, and unit-testable.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def _as_matrix(x) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"expected 2-D matrix, got shape {arr.shape}")
    if arr.size == 0:
        raise ValueError("empty embedding matrix")
    return arr


def centroid(x) -> np.ndarray:
    return _as_matrix(x).mean(axis=0)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 1.0
    sim = float(np.dot(a, b) / (na * nb))
    sim = max(-1.0, min(1.0, sim))
    return 1.0 - sim


def centroid_shift(baseline, current) -> float:
    """Cosine distance between baseline and current centroids."""
    return cosine_distance(centroid(baseline), centroid(current))


def mean_norm(x) -> float:
    return float(np.linalg.norm(_as_matrix(x), axis=1).mean())


def mean_norm_shift(baseline, current) -> float:
    """Relative change in mean L2 norm. Returns 0 if baseline mean is 0."""
    nb = mean_norm(baseline)
    nc = mean_norm(current)
    if nb == 0.0:
        return 0.0 if nc == 0.0 else 1.0
    return abs(nc - nb) / nb


def ks_test_per_dim(baseline, current) -> tuple[float, float]:
    """Return (max-statistic, min-pvalue) over per-dimension Kolmogorov-Smirnov tests.

    A small p-value (< threshold_ks_pvalue) on any dimension indicates that the
    marginal distribution of that dimension shifted between baseline and current.
    """
    b = _as_matrix(baseline)
    c = _as_matrix(current)
    if b.shape[1] != c.shape[1]:
        raise ValueError(f"dimension mismatch: baseline={b.shape[1]} current={c.shape[1]}")
    max_stat = 0.0
    min_p = 1.0
    for d in range(b.shape[1]):
        result = stats.ks_2samp(b[:, d], c[:, d])
        if result.statistic > max_stat:
            max_stat = float(result.statistic)
        if result.pvalue < min_p:
            min_p = float(result.pvalue)
    return max_stat, min_p


def _hist(x: np.ndarray, bins: np.ndarray) -> np.ndarray:
    h, _ = np.histogram(x, bins=bins)
    h = h.astype(np.float64)
    s = h.sum()
    if s == 0.0:
        return h
    return h / s


def jensen_shannon(baseline, current, bins: int = 30) -> float:
    """Jensen-Shannon divergence between norm distributions of baseline and current.

    Uses base-2 log so the value lies in [0, 1].
    """
    b_norms = np.linalg.norm(_as_matrix(baseline), axis=1)
    c_norms = np.linalg.norm(_as_matrix(current), axis=1)
    lo = float(min(b_norms.min(), c_norms.min()))
    hi = float(max(b_norms.max(), c_norms.max()))
    if hi == lo:
        return 0.0
    edges = np.linspace(lo, hi, bins + 1)
    p = _hist(b_norms, edges)
    q = _hist(c_norms, edges)
    m = 0.5 * (p + q)
    eps = 1e-12

    def _kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * (np.log2(a[mask] + eps) - np.log2(b[mask] + eps))))

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)
