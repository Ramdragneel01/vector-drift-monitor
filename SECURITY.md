# Security Policy — vector-drift-monitor

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: **ramprakashdhulipudi@gmail.com**

Include:
- Description and impact
- Reproduction steps or proof-of-concept
- Affected version / commit SHA

We will acknowledge within 72 hours and aim to provide a remediation plan within 7 days for high-severity issues.

## Threat Model (v0.1)

### In Scope

| Class | Surface | Mitigation |
|---|---|---|
| Embedding leakage via `/snapshots/{ns}` | HTTP API | Operate behind an authenticated gateway; do not expose `/snapshots` to the public internet |
| Vector size exhaustion | `/snapshots`, `/check` | Front with a body-size limit (nginx/ingress); future v0.2 ships per-route limits |
| Webhook abuse (alert spam) | `WebhookAlerter` | Errors are swallowed; rate-limit on the receiver side |
| Threshold-config tampering | env / `.env` | Treat env as secret-equivalent; deploy via secret manager |

### Out of Scope (v0.1)

- **Authentication/authorization.** v0.1 has no built-in auth. Run behind a gateway that handles tenant identity and authentication.
- **Embedding privacy guarantees.** Snapshots are stored as raw float matrices. If your embeddings are derived from PII, you must encrypt the storage volume / object store yourself.
- **Multi-tenant accounting integrity.** The in-memory store is per-process; multi-replica deployments must use a shared backend.
- **Network DDoS.** Front with a CDN / WAF.

## Hardening Checklist

If you deploy `vector-drift-monitor`:

- [ ] Run as non-root (provided in the Dockerfile, uid 10001).
- [ ] Restrict `/snapshots`, `/baselines`, `/check` to private networks or behind auth.
- [ ] Mount the storage volume read-write only for this process.
- [ ] Restrict `/metrics` to your scrape network.
- [ ] Treat snapshot data as PII-equivalent unless you have proven otherwise.

## Dependency Security

- Runtime deps pinned in `requirements.txt`.
- `pip-audit` in CI (planned for v0.2).
- Renovate bot enabled day 1.
