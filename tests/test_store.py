import numpy as np
import pytest

from vector_drift_monitor.store import FileStore, InMemoryStore, Snapshot, build_store


def test_snapshot_requires_2d():
    with pytest.raises(ValueError):
        Snapshot(namespace="ns", vectors=np.array([1.0, 2.0]))


def test_snapshot_meta():
    s = Snapshot(namespace="ns", vectors=np.zeros((5, 3)), label="v1")
    meta = s.to_meta()
    assert meta["namespace"] == "ns"
    assert meta["n"] == 5 and meta["dim"] == 3 and meta["label"] == "v1"


def test_inmemory_put_get_list():
    store = InMemoryStore()
    s1 = Snapshot(namespace="a", vectors=np.zeros((2, 4)))
    s2 = Snapshot(namespace="b", vectors=np.zeros((2, 4)))
    store.put(s1)
    store.put(s2)
    assert store.get(s1.id) is s1
    assert [s.id for s in store.list("a")] == [s1.id]


def test_set_baseline_validates():
    store = InMemoryStore()
    s = Snapshot(namespace="a", vectors=np.zeros((2, 4)))
    store.put(s)
    with pytest.raises(KeyError):
        store.set_baseline("a", "nope")
    store.set_baseline("a", s.id)
    assert store.get_baseline("a") is s


def test_set_baseline_namespace_mismatch():
    store = InMemoryStore()
    s = Snapshot(namespace="a", vectors=np.zeros((2, 4)))
    store.put(s)
    with pytest.raises(ValueError):
        store.set_baseline("other", s.id)


def test_filestore_roundtrip(tmp_path):
    store = FileStore(str(tmp_path))
    s = Snapshot(namespace="a", vectors=np.arange(12.0).reshape(3, 4))
    store.put(s)
    store.set_baseline("a", s.id)

    store2 = FileStore(str(tmp_path))
    loaded = store2.get(s.id)
    assert loaded is not None and loaded.namespace == "a" and loaded.dim == 4
    assert store2.get_baseline("a").id == s.id


def test_build_store_unknown_backend_raises():
    with pytest.raises(ValueError):
        build_store("redis", "/tmp/x")
