"""Process-wide metrics and audit ring for the FastAPI service."""
from __future__ import annotations

import threading
from collections import deque

from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

_DECISIONS = Counter("vdm_checks_total", "Drift checks performed", ["namespace", "severity"])
_SNAPSHOTS = Counter("vdm_snapshots_total", "Snapshots ingested", ["namespace"])


class Service:
    """Thin wrapper around the prometheus counters + an audit ring buffer."""

    def __init__(self, audit_capacity: int = 500) -> None:
        self._lock = threading.Lock()
        self._audit: deque[dict] = deque(maxlen=audit_capacity)

    def record_snapshot(self, namespace: str) -> None:
        _SNAPSHOTS.labels(namespace=namespace).inc()

    def record_check(self, report) -> None:
        _DECISIONS.labels(namespace=report.namespace, severity=report.severity).inc()
        with self._lock:
            self._audit.append(report.to_dict())

    def audit(self, namespace: str | None = None, limit: int = 50) -> list[dict]:
        with self._lock:
            items = list(self._audit)
        if namespace is not None:
            items = [r for r in items if r.get("namespace") == namespace]
        return items[-limit:]

    @staticmethod
    def prometheus() -> tuple[bytes, str]:
        return generate_latest(), CONTENT_TYPE_LATEST
