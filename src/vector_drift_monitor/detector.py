"""Drift detection: compose metrics into a thresholded report."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import Settings
from .metrics import centroid_shift, jensen_shannon, ks_test_per_dim, mean_norm_shift
from .store import Snapshot


@dataclass
class DriftReport:
    namespace: str
    baseline_id: str
    current_id: str
    drift: bool
    severity: str  # ok | warn | drift
    centroid_shift: float
    mean_norm_shift: float
    ks_statistic: float
    ks_pvalue: float
    js_divergence: float
    thresholds: dict
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def detect_drift(baseline: Snapshot, current: Snapshot, settings: Settings) -> DriftReport:
    if baseline.namespace != current.namespace:
        raise ValueError("baseline and current must share a namespace")
    if baseline.dim != current.dim:
        raise ValueError(f"dimension mismatch: baseline={baseline.dim} current={current.dim}")

    cs = centroid_shift(baseline.vectors, current.vectors)
    ns = mean_norm_shift(baseline.vectors, current.vectors)
    ks_stat, ks_p = ks_test_per_dim(baseline.vectors, current.vectors)
    js = jensen_shannon(baseline.vectors, current.vectors)

    reasons: list[str] = []
    if cs >= settings.threshold_centroid_shift:
        reasons.append(f"centroid_shift={cs:.4f} >= {settings.threshold_centroid_shift}")
    if ns >= settings.threshold_mean_norm_shift:
        reasons.append(f"mean_norm_shift={ns:.4f} >= {settings.threshold_mean_norm_shift}")
    if ks_p < settings.threshold_ks_pvalue:
        reasons.append(f"ks_pvalue={ks_p:.4g} < {settings.threshold_ks_pvalue}")
    if js >= settings.threshold_js_divergence:
        reasons.append(f"js_divergence={js:.4f} >= {settings.threshold_js_divergence}")

    drift = len(reasons) > 0
    if drift:
        severity = "drift" if len(reasons) >= 2 else "warn"
    else:
        severity = "ok"

    return DriftReport(
        namespace=current.namespace,
        baseline_id=baseline.id,
        current_id=current.id,
        drift=drift,
        severity=severity,
        centroid_shift=cs,
        mean_norm_shift=ns,
        ks_statistic=ks_stat,
        ks_pvalue=ks_p,
        js_divergence=js,
        thresholds={
            "centroid_shift": settings.threshold_centroid_shift,
            "mean_norm_shift": settings.threshold_mean_norm_shift,
            "ks_pvalue": settings.threshold_ks_pvalue,
            "js_divergence": settings.threshold_js_divergence,
        },
        reasons=reasons,
    )
