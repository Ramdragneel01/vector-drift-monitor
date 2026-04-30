# vector-drift-monitor

> **Production-grade embedding drift detection for vector databases.** Snapshot your retrieval embeddings, lock a baseline, and get a thresholded drift report — as a CLI for CI, as a FastAPI service for live RAG, with Prometheus metrics and webhook alerts.

[![CI](https://github.com/Ramdragneel01/vector-drift-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/Ramdragneel01/vector-drift-monitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

---

## Why

Your RAG quality regresses for three reasons that all look the same in logs:

1. The **embedding model** got upgraded.
2. The **document corpus** drifted (new product launches, archived FAQs).
3. The **query distribution** drifted (a holiday spike, a new tenant).

`vector-drift-monitor` is a single layer that quantifies each of these as a number, fails CI when the number crosses a threshold, and alerts you in production when it crosses again.

It computes four complementary metrics on snapshots of your embedding population:

| Metric             | Catches                                              |
| ------------------ | ---------------------------------------------------- |
| `centroid_shift`   | The "new model has a different center of mass" bug   |
| `mean_norm_shift`  | The "embeddings got rescaled" bug                    |
| `ks_pvalue`        | Per-dimension marginal distribution shift            |
| `js_divergence`    | Norm-distribution shift, base-2, capped at 1         |

A report is a `drift` boolean, a `severity` (`ok | warn | drift`), and human-readable reasons.

---

## Quickstart

### CLI (CI-friendly)

```bash
pip install vector-drift-monitor

vdm check \
  --baseline embeddings_v1.npy \
  --current  embeddings_v2.npy \
  --namespace product-catalog
```

Exit code is `2` on drift — drop it into a GitHub Action and it will fail the build.

### Service

```bash
docker run --rm -p 8091:8091 ghcr.io/ramdragneel01/vector-drift-monitor:latest

# Post a baseline
curl -X POST http://localhost:8091/snapshots \
  -H 'content-type: application/json' \
  -d '{"namespace":"prod","vectors":[[0.1,0.2,0.3],[0.1,0.25,0.31]]}'

# Run a live check (auto-promotes first snapshot to baseline)
curl -X POST http://localhost:8091/check/prod \
  -H 'content-type: application/json' \
  -d '{"vectors":[[0.4,0.4,0.4]]}'
```

### Compose

```bash
docker compose up --build
```

---

## Endpoints

| Method | Path                                | Purpose                                           |
| ------ | ----------------------------------- | ------------------------------------------------- |
| `GET`  | `/health`                           | Liveness                                          |
| `GET`  | `/ready`                            | Readiness                                         |
| `GET`  | `/metrics`                          | Prometheus exposition                             |
| `POST` | `/snapshots`                        | Ingest a snapshot                                 |
| `GET`  | `/snapshots/{namespace}`            | List snapshots for a namespace                    |
| `POST` | `/baselines/{namespace}/{snap_id}`  | Mark a snapshot as the baseline                   |
| `GET`  | `/baselines/{namespace}`            | Show current baseline                             |
| `POST` | `/check/{namespace}`                | Ingest current snapshot and return a drift report |
| `GET`  | `/reports/{namespace}`              | Audit ring of recent reports                      |

---

## Configuration

All variables are prefixed with `VDM_`. See [.env.example](.env.example).

| Var                              | Default       | Notes                                  |
| -------------------------------- | ------------- | -------------------------------------- |
| `VDM_THRESHOLD_CENTROID_SHIFT`   | `0.10`        | Cosine distance between centroids      |
| `VDM_THRESHOLD_MEAN_NORM_SHIFT`  | `0.10`        | Relative L2 norm change                |
| `VDM_THRESHOLD_KS_PVALUE`        | `0.01`        | Min p-value before flagging drift      |
| `VDM_THRESHOLD_JS_DIVERGENCE`    | `0.10`        | Max Jensen-Shannon divergence          |
| `VDM_STORAGE_BACKEND`            | `memory`      | `memory` or `file`                     |
| `VDM_STORAGE_PATH`               | `./data/...`  | Where the file backend persists        |
| `VDM_ALERT_WEBHOOK_URL`          | (empty)       | Slack-compatible incoming webhook      |

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

38 tests covering metrics math, snapshot model + storage backends (in-memory + file roundtrip), the detector, the FastAPI app (mocked transport), and the CLI.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md). The pipeline is intentionally simple:

```
  embeddings ─▶ Snapshot ─▶ Store ─┐
                                   ├─▶ detect_drift() ─▶ DriftReport ─▶ alerter / metrics / audit
  baseline ──▶ Snapshot ─▶ Store ─┘
```

Every metric is a pure function on numpy arrays. Storage and HTTP are thin shells around it.

---

## Roadmap

- [ ] OTLP exporter for OpenTelemetry-native pipelines
- [ ] Per-field drift on metadata sidecar (e.g., source, lang, tenant)
- [ ] Streaming ingestion (windowed snapshots from Kafka)
- [ ] Coverage-aware alerting (penalize sparse comparisons)
- [ ] Native integration with [`rag-firewall`](https://github.com/Ramdragneel01/rag-firewall) and [`agent-cost-governor`](https://github.com/Ramdragneel01/agent-cost-governor)

Part of the **Production AI, From Zero** series — see the [companion Medium article](https://medium.com/@RamPrakashD).

---

## License

[MIT](LICENSE) © Ram Prakash Dhulipudi
