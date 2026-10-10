"""Container command lines and stats hand-off (no Docker needed)."""
import json
import subprocess
import sys
from pathlib import Path

from omrbench import containers
from omrbench.monitor import RunStats

ROOT = Path(__file__).resolve().parent.parent


def test_run_cmd_mounts_gpu_and_monitor(tmp_path):
    cmd = containers.run_cmd("omrbench/homr:0.7.0", ["homr", "p.png"],
                             mounts={tmp_path: "/work", tmp_path / "m": "/models"}, gpu=True,
                             read_only={"/models"})
    assert cmd[:4] == ["docker", "run", "--rm", "--gpus"]
    assert f"{tmp_path}:/work" in cmd and f"{tmp_path / 'm'}:/models:ro" in cmd
    assert cmd[-6:] == ["omr-run", "--stats", "/work/stats.json", "--", "homr", "p.png"]


def test_run_cmd_without_gpu_has_no_gpus_flag(tmp_path):
    assert "--gpus" not in containers.run_cmd("img", ["x"], mounts={tmp_path: "/work"})


def test_build_cmd_passes_base_image():
    cmd = containers.build_cmd("homr")
    assert "BASE_IMAGE=omrbench/base:cuda" in cmd
    assert cmd[-1].endswith("docker/homr")


def test_every_image_has_a_dockerfile():
    for name, (_, ctx, _) in containers.IMAGES.items():
        assert (ROOT / "docker" / ctx / "Dockerfile").exists(), name


def test_stats_read_back_from_work_dir(tmp_path, monkeypatch):
    def fake_run(cmd, *, log_path, timeout_s=None, **_):
        (tmp_path / "stats.json").write_text(json.dumps(
            {"wall_s": 3.5, "peak_rss_mb": 900.0, "peak_gpu_mem_mb": 1500.0, "exit_code": 0,
             "cpu_user_s": 2.0, "cpu_sys_s": 0.5, "commands": ["homr p.png"], "unknown": 1}))
        return RunStats(wall_s=4.0, exit_code=0)
    monkeypatch.setattr(containers, "run_monitored", fake_run)
    st = containers.run_in_container("img", ["homr"], mounts={tmp_path: "/work"},
                                     log_path=tmp_path / "log.txt")
    assert st.wall_s == 3.5 and st.peak_gpu_mem_mb == 1500.0 and st.cpu_s == 2.5


def test_host_stats_used_when_omr_run_wrote_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(containers, "run_monitored", lambda *a, **k: RunStats(wall_s=1.0, exit_code=125))
    st = containers.run_in_container("img", ["x"], mounts={tmp_path: "/work"}, log_path=tmp_path / "l.txt")
    assert st.exit_code == 125


def test_omr_run_writes_stats_for_a_command(tmp_path):
    out = subprocess.run(
        [sys.executable,
         str(ROOT / "docker" / "base" / "omr_run.py"),
         "--stats", str(tmp_path / "stats.json"), "--", sys.executable, "-c", "import time; time.sleep(0.3)"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    data = json.loads((tmp_path / "stats.json").read_text())
    assert data["exit_code"] == 0 and data["wall_s"] >= 0.3 and data["peak_rss_mb"] > 0
