"""FastAPI HTTP surface."""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .alerts import Alerter, build_alerter
from .config import Settings
from .detector import detect_drift
from .service import Service
from .store import InMemoryStore, Snapshot, build_store


class SnapshotIn(BaseModel):
    namespace: str = Field(..., min_length=1)
    vectors: list[list[float]] = Field(..., min_length=1)
    label: str = ""


class CheckIn(BaseModel):
    vectors: list[list[float]] = Field(..., min_length=1)
    label: str = ""
    set_baseline_if_missing: bool = True


def create_app(
    settings: Settings | None = None,
    store: InMemoryStore | None = None,
    alerter: Alerter | None = None,
    svc: Service | None = None,
) -> FastAPI:
    settings = settings or Settings()
    store = store or build_store(settings.storage_backend, settings.storage_path)
    alerter = alerter or build_alerter(settings.alert_webhook_url)
    svc = svc or Service()

    app = FastAPI(title="vector-drift-monitor", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/ready")
    def ready() -> dict[str, Any]:
        return {"status": "ready"}

    @app.get("/metrics")
    def metrics() -> Response:
        body, ctype = svc.prometheus()
        return Response(content=body, media_type=ctype)

    @app.post("/snapshots", status_code=201)
    def post_snapshot(payload: SnapshotIn) -> dict[str, Any]:
        try:
            snap = Snapshot(namespace=payload.namespace, vectors=np.array(payload.vectors), label=payload.label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        store.put(snap)
        svc.record_snapshot(snap.namespace)
        return snap.to_meta()

    @app.post("/baselines/{namespace}/{snapshot_id}", status_code=200)
    def set_baseline(namespace: str, snapshot_id: str) -> dict[str, Any]:
        try:
            store.set_baseline(namespace, snapshot_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        return {"namespace": namespace, "baseline_id": snapshot_id}

    @app.get("/baselines/{namespace}")
    def get_baseline(namespace: str) -> dict[str, Any]:
        b = store.get_baseline(namespace)
        if b is None:
            raise HTTPException(status_code=404, detail="no baseline set")
        return b.to_meta()

    @app.post("/check/{namespace}")
    def check(namespace: str, payload: CheckIn) -> JSONResponse:
        try:
            current = Snapshot(namespace=namespace, vectors=np.array(payload.vectors), label=payload.label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        store.put(current)
        svc.record_snapshot(namespace)

        baseline = store.get_baseline(namespace)
        if baseline is None:
            if payload.set_baseline_if_missing:
                store.set_baseline(namespace, current.id)
                return JSONResponse(
                    status_code=200,
                    content={
                        "namespace": namespace,
                        "current_id": current.id,
                        "baseline_id": current.id,
                        "drift": False,
                        "severity": "ok",
                        "reasons": ["no prior baseline; current snapshot promoted to baseline"],
                    },
                )
            raise HTTPException(status_code=409, detail="no baseline set for namespace")

        try:
            report = detect_drift(baseline, current, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        svc.record_check(report)
        if report.drift:
            try:
                alerter.fire(report)
            except Exception:
                pass
        return JSONResponse(content=report.to_dict())

    @app.get("/reports/{namespace}")
    def reports(namespace: str, limit: int = 50) -> list[dict[str, Any]]:
        return svc.audit(namespace=namespace, limit=limit)

    @app.get("/snapshots/{namespace}")
    def list_snapshots(namespace: str) -> list[dict[str, Any]]:
        return [s.to_meta() for s in store.list(namespace=namespace)]

    return app


# Module-level app for `uvicorn vector_drift_monitor.app:app` style.
app = create_app()
