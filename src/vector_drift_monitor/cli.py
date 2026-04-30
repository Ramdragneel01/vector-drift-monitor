"""Click CLI for offline / CI-time drift checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import numpy as np
from rich.console import Console
from rich.table import Table

from .config import Settings
from .detector import detect_drift
from .store import Snapshot

console = Console()


def _load_vectors(path: str) -> np.ndarray:
    p = Path(path)
    if p.suffix == ".npy":
        return np.load(p)
    if p.suffix in {".json", ""}:
        return np.asarray(json.loads(p.read_text()))
    raise click.ClickException(f"unsupported vectors file: {path}")


@click.group()
@click.version_option(package_name="vector-drift-monitor")
def cli() -> None:
    """vector-drift-monitor CLI."""


@cli.command("check")
@click.option("--baseline", "baseline_path", required=True, type=click.Path(exists=True))
@click.option("--current", "current_path", required=True, type=click.Path(exists=True))
@click.option("--namespace", default="default")
@click.option("--out", "out_path", type=click.Path(), default=None, help="Write the report JSON to this path.")
@click.option("--fail-on-drift/--no-fail-on-drift", default=True)
def check_cmd(baseline_path: str, current_path: str, namespace: str, out_path: str | None, fail_on_drift: bool) -> None:
    """Run a drift check between two saved embedding matrices."""
    baseline = Snapshot(namespace=namespace, vectors=_load_vectors(baseline_path), label="baseline")
    current = Snapshot(namespace=namespace, vectors=_load_vectors(current_path), label="current")
    report = detect_drift(baseline, current, Settings())

    table = Table(title=f"Drift Report — {namespace}", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_row("centroid_shift", f"{report.centroid_shift:.4f}", f"{report.thresholds['centroid_shift']:.4f}")
    table.add_row("mean_norm_shift", f"{report.mean_norm_shift:.4f}", f"{report.thresholds['mean_norm_shift']:.4f}")
    table.add_row("ks_pvalue", f"{report.ks_pvalue:.4g}", f"{report.thresholds['ks_pvalue']:.4g}")
    table.add_row("js_divergence", f"{report.js_divergence:.4f}", f"{report.thresholds['js_divergence']:.4f}")
    console.print(table)
    color = {"ok": "green", "warn": "yellow", "drift": "red"}[report.severity]
    console.print(f"[{color}]severity={report.severity}  drift={report.drift}[/]")
    if report.reasons:
        for r in report.reasons:
            console.print(f"  • {r}")

    if out_path:
        Path(out_path).write_text(json.dumps(report.to_dict(), indent=2))

    if report.drift and fail_on_drift:
        sys.exit(2)


@cli.command("score")
@click.option("--baseline", "baseline_path", required=True, type=click.Path(exists=True))
@click.option("--current", "current_path", required=True, type=click.Path(exists=True))
def score_cmd(baseline_path: str, current_path: str) -> None:
    """Print a single JSON report (no thresholding) for piping."""
    report = detect_drift(
        Snapshot(namespace="cli", vectors=_load_vectors(baseline_path), label="baseline"),
        Snapshot(namespace="cli", vectors=_load_vectors(current_path), label="current"),
        Settings(),
    )
    click.echo(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    cli()
