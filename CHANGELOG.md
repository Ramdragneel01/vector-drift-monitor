# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and the project follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-30

### Added
- Snapshot model + thread-safe `InMemoryStore` and `FileStore` backends (`vector_drift_monitor.store`).
- Pure-function drift metrics: centroid shift, mean-norm shift, per-dim KS test, Jensen-Shannon divergence on norms (`vector_drift_monitor.metrics`).
- Thresholded `detect_drift()` returning a `DriftReport(drift, severity, reasons, ...)` (`vector_drift_monitor.detector`).
- Webhook alerter with safe failure mode (`vector_drift_monitor.alerts`).
- FastAPI service with endpoints: `/health`, `/ready`, `/metrics`, `/snapshots`, `/baselines/{ns}/{id}`, `/baselines/{ns}`, `/check/{ns}`, `/reports/{ns}`, `/snapshots/{ns}` (`vector_drift_monitor.app`).
- Click CLI: `vdm check` (CI-friendly, exit code 2 on drift) and `vdm score` (raw JSON).
- Test suite (38 tests across metrics, store, detector, app, CLI).
- Dockerfile (non-root uid 10001, healthcheck, python:3.11-slim).
- `docker-compose.yml`, `.env.example`.
- CI: ruff lint, pytest with coverage, container smoke test, GHCR publish on tag.

[0.1.0]: https://github.com/Ramdragneel01/vector-drift-monitor/releases/tag/v0.1.0
