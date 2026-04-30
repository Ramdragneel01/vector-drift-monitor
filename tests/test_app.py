import numpy as np
from fastapi.testclient import TestClient

from vector_drift_monitor.app import create_app
from vector_drift_monitor.config import Settings
from vector_drift_monitor.service import Service
from vector_drift_monitor.store import InMemoryStore


def _client():
    return TestClient(create_app(Settings(), InMemoryStore(), svc=Service()))


def test_health_and_metrics():
    c = _client()
    assert c.get("/health").json()["status"] == "ok"
    r = c.get("/metrics")
    assert r.status_code == 200
    assert "vdm_checks_total" in r.text or "vdm_snapshots_total" in r.text or "python_info" in r.text


def test_post_snapshot_and_set_baseline():
    c = _client()
    rng = np.random.default_rng(11)
    payload = {"namespace": "ns", "vectors": rng.standard_normal((50, 8)).tolist(), "label": "v1"}
    r = c.post("/snapshots", json=payload)
    assert r.status_code == 201
    snap_id = r.json()["id"]

    r = c.post(f"/baselines/ns/{snap_id}")
    assert r.status_code == 200
    r = c.get("/baselines/ns")
    assert r.json()["id"] == snap_id


def test_post_snapshot_invalid_dimensions():
    c = _client()
    r = c.post("/snapshots", json={"namespace": "ns", "vectors": [[]]})
    assert r.status_code == 422 or r.status_code == 400


def test_check_promotes_baseline_when_missing():
    c = _client()
    rng = np.random.default_rng(12)
    payload = {"vectors": rng.standard_normal((30, 4)).tolist()}
    r = c.post("/check/ns2", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["drift"] is False
    assert body["baseline_id"] == body["current_id"]


def test_check_returns_drift_when_translated():
    c = _client()
    rng = np.random.default_rng(13)
    base = rng.standard_normal((200, 8))
    cur = rng.standard_normal((200, 8)) + 3.0

    r = c.post("/snapshots", json={"namespace": "ns3", "vectors": base.tolist()})
    sid = r.json()["id"]
    c.post(f"/baselines/ns3/{sid}")

    r = c.post("/check/ns3", json={"vectors": cur.tolist()})
    body = r.json()
    assert body["drift"] is True
    assert body["severity"] == "drift"


def test_get_baseline_404_when_missing():
    c = _client()
    r = c.get("/baselines/nope")
    assert r.status_code == 404


def test_set_baseline_404_for_unknown_snapshot():
    c = _client()
    r = c.post("/baselines/ns/does-not-exist")
    assert r.status_code == 404


def test_list_snapshots():
    c = _client()
    rng = np.random.default_rng(14)
    c.post("/snapshots", json={"namespace": "ns4", "vectors": rng.standard_normal((10, 4)).tolist()})
    c.post("/snapshots", json={"namespace": "ns4", "vectors": rng.standard_normal((10, 4)).tolist()})
    r = c.get("/snapshots/ns4")
    assert r.status_code == 200 and len(r.json()) == 2
