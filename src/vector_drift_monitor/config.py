"""Typed configuration via env vars (VDM_ prefix)."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VDM_", env_file=".env", extra="ignore")

    service_name: str = "vector-drift-monitor"
    host: str = "0.0.0.0"
    port: int = 8091
    log_level: str = "INFO"

    # Drift thresholds (drift declared if any metric exceeds its threshold).
    threshold_centroid_shift: float = Field(0.10, description="Cosine distance between centroids")
    threshold_mean_norm_shift: float = Field(0.10, description="Relative L2 norm change")
    threshold_ks_pvalue: float = Field(0.01, description="Min KS p-value before flagging drift")
    threshold_js_divergence: float = Field(0.10, description="Max Jensen-Shannon divergence")

    # Storage
    storage_backend: str = Field("memory", description="memory | file")
    storage_path: str = "./data/snapshots"

    # Alerts
    alert_webhook_url: str = ""
