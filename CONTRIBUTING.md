# Contributing

Thanks for considering a contribution!

## Dev Setup

```bash
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest
```

## Standards

- Python 3.10+ with type hints.
- `ruff check src tests` must be clean.
- Tests for every new behaviour. Aim ≥ 85% coverage.
- Pure functions where possible — keep math, IO, and HTTP separate.
- One feature per PR; keep diffs small.

## Branching

- `main` is always shippable.
- Open a PR against `main`.

## Commit Messages

Conventional commits preferred:

```
feat(metrics): add MMD with rbf kernel
fix(store): persist baseline pointer atomically
docs(readme): add CI exit-code section
```

## Good First PRs

- New drift metrics (energy distance, MMD)
- A new storage backend (Redis, Postgres, S3)
- Better CLI output (markdown, html)
- Tests for edge cases (singleton baseline, identical-vector populations)

## Code of Conduct

Be kind, technical, and brief. Mean reviews aren't accepted; mean code is.
