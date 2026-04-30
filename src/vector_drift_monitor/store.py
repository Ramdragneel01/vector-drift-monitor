"""Snapshot model and storage backends."""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


@dataclass
class Snapshot:
    """An immutable point-in-time capture of an embedding population."""
    namespace: str
    vectors: np.ndarray  # shape: (n, dim)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    label: str = ""

    def __post_init__(self):
        v = np.asarray(self.vectors, dtype=np.float64)
        if v.ndim != 2 or v.size == 0:
            raise ValueError(f"vectors must be a non-empty 2-D matrix; got shape {v.shape}")
        self.vectors = v

    @property
    def n(self) -> int:
        return int(self.vectors.shape[0])

    @property
    def dim(self) -> int:
        return int(self.vectors.shape[1])

    def to_meta(self) -> dict:
        return {
            "id": self.id,
            "namespace": self.namespace,
            "created_at": self.created_at,
            "label": self.label,
            "n": self.n,
            "dim": self.dim,
        }


class InMemoryStore:
    """Thread-safe in-memory snapshot store with per-namespace baseline pointer."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshots: dict[str, Snapshot] = {}
        self._baselines: dict[str, str] = {}  # namespace -> snapshot id

    def put(self, snap: Snapshot) -> Snapshot:
        with self._lock:
            self._snapshots[snap.id] = snap
        return snap

    def get(self, snapshot_id: str) -> Snapshot | None:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list(self, namespace: str | None = None) -> list[Snapshot]:
        with self._lock:
            items = list(self._snapshots.values())
        if namespace is not None:
            items = [s for s in items if s.namespace == namespace]
        return sorted(items, key=lambda s: s.created_at)

    def set_baseline(self, namespace: str, snapshot_id: str) -> None:
        with self._lock:
            if snapshot_id not in self._snapshots:
                raise KeyError(f"unknown snapshot {snapshot_id}")
            if self._snapshots[snapshot_id].namespace != namespace:
                raise ValueError("snapshot namespace does not match")
            self._baselines[namespace] = snapshot_id

    def get_baseline(self, namespace: str) -> Snapshot | None:
        with self._lock:
            sid = self._baselines.get(namespace)
            return self._snapshots.get(sid) if sid else None


class FileStore(InMemoryStore):
    """File-backed store: vectors are persisted as .npy and metadata as .json.

    This is a simple deployment-friendly option. For production at scale, use
    the in-memory store fronted by your existing object store / DB.
    """

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    def _path(self, snap_id: str) -> Path:
        return self._root / snap_id

    def put(self, snap: Snapshot) -> Snapshot:
        super().put(snap)
        p = self._path(snap.id)
        p.mkdir(parents=True, exist_ok=True)
        np.save(p / "vectors.npy", snap.vectors)
        (p / "meta.json").write_text(json.dumps(snap.to_meta()))
        self._persist_baselines()
        return snap

    def set_baseline(self, namespace: str, snapshot_id: str) -> None:
        super().set_baseline(namespace, snapshot_id)
        self._persist_baselines()

    def _persist_baselines(self) -> None:
        (self._root / "baselines.json").write_text(json.dumps(self._baselines))

    def _load(self) -> None:
        if not self._root.exists():
            return
        for child in self._root.iterdir():
            if not child.is_dir():
                continue
            meta_p = child / "meta.json"
            vec_p = child / "vectors.npy"
            if not meta_p.exists() or not vec_p.exists():
                continue
            meta = json.loads(meta_p.read_text())
            vectors = np.load(vec_p)
            snap = Snapshot(
                namespace=meta["namespace"],
                vectors=vectors,
                id=meta["id"],
                created_at=meta["created_at"],
                label=meta.get("label", ""),
            )
            self._snapshots[snap.id] = snap
        bp = self._root / "baselines.json"
        if bp.exists():
            try:
                self._baselines.update(json.loads(bp.read_text()))
            except json.JSONDecodeError:
                pass


def build_store(backend: str, path: str) -> InMemoryStore:
    backend = (backend or "memory").lower()
    if backend == "memory":
        return InMemoryStore()
    if backend == "file":
        return FileStore(path)
    raise ValueError(f"unknown storage backend: {backend!r}")
