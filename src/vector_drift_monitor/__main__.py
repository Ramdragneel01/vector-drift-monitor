"""Uvicorn entry point: `python -m vector_drift_monitor`."""
from __future__ import annotations

import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "vector_drift_monitor.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
