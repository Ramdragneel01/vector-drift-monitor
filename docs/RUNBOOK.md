# Runbook — vector-drift-monitor

Operational guide for on-call engineers.

## 1. Deploy

### Container

```bash
docker run -d --name vdm --restart unless-stopped \
  -p 8091:8091 \
  -e VDM_STORAGE_BACKEND=file \
  -e VDM_STORAGE_PATH=/data/snapshots \
  -e VDM_ALERT_WEBHOOK_URL=$SLACK_WEBHOOK \
  -v /var/lib/vdm:/data \
  ghcr.io/ramdragneel01/vector-drift-monitor:latest
```

Verify:

```bash
curl -fsS http://localhost:8091/health
curl -fsS http://localhost:8091/metrics | grep vdm_
```

### Kubernetes

A starter manifest is left for the operator (Deployment + Service + PersistentVolumeClaim mounting `/data`). For multi-replica deployments use the file backend with shared NFS or implement a database-backed store; the in-memory store is single-replica only.

## 2. Capture a Baseline

For each retrieval namespace (e.g., `product-catalog`, `tenant-acme`):

```bash
# Pull a representative slice of vectors out of your vector DB.
# A few thousand is usually enough.
python tools/dump_baseline.py > baseline.json

curl -X POST http://vdm/snapshots \
  -H 'content-type: application/json' \
  -d @baseline.json    # {"namespace": "...", "vectors": [...]}

# Take the returned id and lock it as the baseline:
curl -X POST http://vdm/baselines/product-catalog/<snapshot_id>
```

## 3. Tune Thresholds

Defaults are conservative. For a high-frequency hourly check, raise `VDM_THRESHOLD_KS_PVALUE` to `1e-4` to reduce false positives from RNG sampling effects.

For a once-a-day check on a stable corpus, the defaults are fine.

`severity = drift` means *two or more* metrics fired. `severity = warn` means one. Page only on `drift`.

## 4. Re-baseline

When you intentionally change the embedding model or rebuild the corpus:

1. Capture a fresh snapshot post-deploy.
2. `POST /baselines/{ns}/{new_snapshot_id}`.
3. Note the change in your team channel — old reports are now invalid.

## 5. Alert Playbooks

### `severity=drift` page

1. `GET /reports/{namespace}?limit=5` — see the most recent reports.
2. Eyeball which metric(s) tripped.
3. If `centroid_shift` only → suspect new embedding model or new tenant onboarded.
4. If `mean_norm_shift` only → embedding service is mis-normalizing.
5. If KS p-value tiny → marginal drift on specific dimensions; usually corpus drift.
6. If JS divergence high → norm distribution shifted (e.g., new doc class).

### Webhook flood

If `VDM_ALERT_WEBHOOK_URL` is firing too often:
- Raise thresholds.
- Add deduplication on the receiver (Slack thread, PagerDuty grouping).
- Switch to once-per-day batched checks via the CLI in CI instead of live `/check`.

### Disk pressure (file backend)

The file store is append-only. Rotate snapshot directories monthly, or move to in-memory + external persistence.

## 6. Key Metrics

| Metric                                           | Type    | Meaning                              |
| ------------------------------------------------ | ------- | ------------------------------------ |
| `vdm_checks_total{namespace, severity}`          | counter | severity ∈ {ok, warn, drift}         |
| `vdm_snapshots_total{namespace}`                 | counter | Snapshots ingested                   |

Suggested alerts:
- `increase(vdm_checks_total{severity="drift"}[15m]) > 0`
- `absent(vdm_checks_total{namespace="product-catalog"}) for 1h` — drift checks stopped running

## 7. CI Integration

Add a step that runs `vdm check` against a fixed baseline:

```yaml
- run: |
    vdm check \
      --baseline ci/baseline.npy \
      --current  ci/current.npy \
      --namespace product-catalog
```

Exit code `2` fails the build on drift.
