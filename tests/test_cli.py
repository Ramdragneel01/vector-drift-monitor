import json

import numpy as np
from click.testing import CliRunner

from vector_drift_monitor.cli import cli


def _write_npy(path, arr):
    np.save(path, arr)


def test_cli_check_no_drift(tmp_path):
    rng = np.random.default_rng(15)
    base = tmp_path / "base.npy"
    cur = tmp_path / "cur.npy"
    _write_npy(base, rng.standard_normal((200, 4)))
    _write_npy(cur, rng.standard_normal((200, 4)))

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--baseline", str(base), "--current", str(cur), "--no-fail-on-drift"])
    assert result.exit_code == 0
    assert "Drift Report" in result.output


def test_cli_check_drift_returns_exit_code_2(tmp_path):
    rng = np.random.default_rng(16)
    base = tmp_path / "base.npy"
    cur = tmp_path / "cur.npy"
    _write_npy(base, rng.standard_normal((300, 4)))
    _write_npy(cur, rng.standard_normal((300, 4)) + 5.0)

    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["check", "--baseline", str(base), "--current", str(cur), "--out", str(out_file)]
    )
    assert result.exit_code == 2
    rep = json.loads(out_file.read_text())
    assert rep["drift"] is True


def test_cli_score_outputs_json(tmp_path):
    rng = np.random.default_rng(17)
    base = tmp_path / "base.npy"
    cur = tmp_path / "cur.npy"
    _write_npy(base, rng.standard_normal((100, 4)))
    _write_npy(cur, rng.standard_normal((100, 4)))

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--baseline", str(base), "--current", str(cur)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "centroid_shift" in payload
