# Architecture — vector-drift-monitor

## Goal

Make embedding drift a measurable, actionable, ops-visible thing. Do it without a sidecar database, without a learning curve, and without coupling to any single vector store.

## Component View

```
                ┌─────────────────────────────────────────────────┐
                │              vector-drift-monitor                │
 client ──HTTP──▶                                                 │
                │  ┌────────────┐   ┌───────────┐   ┌──────────┐  │
                │  │ Snapshot   │──▶│  Store    │──▶│ Detector │──┼──▶ DriftReport
                │  └────────────┘   └───────────┘   └──────────┘  │
                │                                       │         │
                │                                       ▼         │
                │                              ┌──────────────┐   │
                │                              │   Alerter    │──▶│ Webhook
                │                              └──────────────┘   │
                │                                                 │
                │                       /metrics  /reports  /stats │
                └─────────────────────────────────────────────────┘
```

## Module Map

| Module                              | Responsibility                                       |
| ----------------------------------- | ---------------------------------------------------- |
| `vector_drift_monitor.config`       | Pydantic Settings, env-driven thresholds + storage   |
| `vector_drift_monitor.metrics`      | Pure-function drift math on numpy matrices           |
| `vector_drift_monitor.store`        | Snapshot dataclass + `InMemoryStore` / `FileStore`   |
| `vector_drift_monitor.detector`     | `detect_drift()` — composes metrics, applies thresholds |
| `vector_drift_monitor.alerts`       | Webhook alerter, fire-and-forget, never crashes      |
| `vector_drift_monitor.service`      | Process-wide Prometheus counters + audit ring        |
| `vector_drift_monitor.app`          | FastAPI surface, JSON IO                             |
| `vector_drift_monitor.cli`          | Click CLI: `vdm check`, `vdm score`                  |

## Snapshot

A `Snapshot` is an immutable record of `(namespace, vectors, id, created_at, label)`. Vectors are stored as a 2-D `np.float64` matrix. The store is keyed by snapshot id and a separate `namespace → baseline_id` map points at the active baseline.

Two backends ship in v0.1:

- `InMemoryStore` — single-process, thread-safe (lock-protected dicts).
- `FileStore` — persists each snapshot as `vectors.npy` + `meta.json` and the baseline pointer as `baselines.json`. Reload on construction.

Adding a Postgres / S3 backend is a matter of subclassing `InMemoryStore` and overriding `put` / `set_baseline` / `_load`.

## Drift Math

Each metric is a pure function. They are combined in `detector.detect_drift`:

| Metric             | Implementation                                                                 |
| ------------------ | ------------------------------------------------------------------------------ |
| `centroid_shift`   | `1 - cosine_similarity(mean(baseline), mean(current))`                         |
| `mean_norm_shift`  | `\|mean(\|c\|) - mean(\|b\|)\| / mean(\|b\|)`                                   |
| `ks_pvalue`        | `scipy.stats.ks_2samp` per dimension, return min p-value                       |
| `js_divergence`    | Jensen-Shannon divergence on histogrammed L2 norms (base-2, range [0, 1])       |

`DriftReport` records each metric, the threshold it was compared against, and a human-readable `reasons` list. Severity: `ok` (no reason fired), `warn` (one reason), `drift` (two or more).

## Pure-Function Decision

`detect_drift(baseline, current, settings) -> DriftReport`

No HTTP, no async, no globals. Every drift rule is unit-testable in milliseconds. Same pattern as the rest of the production AI series — see `agent-cost-governor.routing.decide` and `rag-firewall.scan_input`.

## Trade-offs Recorded for v0.2

- **No metadata sidecar.** Drift on `source`/`lang` filters often matters more than mean-norm; v0.2 ships a metadata sidecar.
- **Histograms are univariate.** JS divergence here is on the *norm distribution* and KS is per-dimension marginals; multivariate MMD is the v0.2 path.
- **No streaming windowing.** Snapshots are explicit; rolling-window mode arrives with the Kafka adapter.
- **In-memory metrics counters.** Reset on restart; OTLP exporter on the roadmap.

## Operational Targets (v0.1)

- p95 added latency for `/check`: ≤ 50ms for 1k × 768d on a single core
- Image size: ≤ 280MB
- Test coverage: ≥ 85% on `src/vector_drift_monitor/`

## Extension Points

- `metrics.*` — add new pure-function metrics (e.g., MMD, energy distance)
- `store.InMemoryStore` — subclass for new persistence backends
- `alerts.Alerter` — Slack blocks, PagerDuty, queue-backed
- `cli` — add an `ingest` command that runs against a vector DB
