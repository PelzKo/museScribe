"""Container command lines and stats hand-off (no Docker needed)."""
import json
import os
import subprocess
import sys
from pathlib import Path

from omrbench import containers
from omrbench.monitor import RunStats

ROOT = Path(__file__).resolve().parent.parent


def test_run_cmd_runs_as_host_user_and_mounts_identical_paths(tmp_path):
    cmd = containers.run_cmd("omrbench/homr:0.7.0", ["homr", "p.png"],
                             mounts={tmp_path: str(tmp_path)}, gpu=True, cwd=str(tmp_path),
                             stats_file=f"{tmp_path}/stats.json")
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert ["--user", f"{os.getuid()}:{os.getgid()}"] == cmd[3:5]
    assert "--gpus" in cmd and "all" in cmd
    assert f"{tmp_path}:{tmp_path}" in cmd
    assert cmd[cmd.index("-w") + 1] == str(tmp_path)
    assert cmd[cmd.index("omr-run"):] == ["omr-run", "--stats", f"{tmp_path}/stats.json", "--", "homr", "p.png"]


def test_run_cmd_without_gpu_or_stats(tmp_path):
    cmd = containers.run_cmd("img", ["x"], mounts={tmp_path: str(tmp_path)})
    assert "--gpus" not in cmd and "omr-run" not in cmd
    assert cmd[-2:] == ["img", "x"]


def test_env_is_passed_as_e_flags(tmp_path):
    cmd = containers.run_cmd("img", ["x"], mounts={}, env={"JAVA_TOOL_OPTIONS": "-Dx=1"})
    i = cmd.index("JAVA_TOOL_OPTIONS=-Dx=1")
    assert cmd[i - 1] == "-e"


def test_pool_cmd_is_interactive_and_runs_the_worker(tmp_path):
    cmd = containers.pool_cmd("omrbench/homr:0.7.0", mounts={tmp_path: str(tmp_path)}, gpu=True, env={})
    assert "-i" in cmd
    assert cmd[-2:] == [containers.HOMR_WORKER, containers.HOMR_WORKER_SCRIPT]


def test_build_cmd_uses_repo_root_context():
    cmd = containers.build_cmd("homr")
    assert "BASE_IMAGE=omrbench/base:cuda13" in cmd
    assert cmd[cmd.index("-f") + 1].endswith("docker/homr/Dockerfile")
    assert cmd[-1] == str(ROOT)


def test_every_image_has_a_dockerfile():
    for name, (_, ctx, _) in containers.IMAGES.items():
        assert (ROOT / "docker" / ctx / "Dockerfile").exists(), name


def test_homr_worker_is_copied_from_the_single_source():
    text = (ROOT / "docker" / "homr" / "Dockerfile").read_text()
    assert "COPY omrbench/engines/_homr_worker.py /opt/homr/worker.py" in text


def test_stats_read_back_from_workdir(tmp_path, monkeypatch):
    def fake_run(cmd, *, log_path, timeout_s=None, **_):
        (tmp_path / "stats.json").write_text(json.dumps(
            {"wall_s": 3.5, "peak_rss_mb": 900.0, "peak_gpu_mem_mb": 1500.0, "exit_code": 0,
             "cpu_user_s": 2.0, "cpu_sys_s": 0.5, "commands": ["homr p.png"], "unknown": 1}))
        return RunStats(wall_s=4.0, exit_code=0)
    monkeypatch.setattr(containers, "run_monitored", fake_run)
    st = containers.run_in_container("img", ["homr"], workdir=tmp_path, log_path=tmp_path / "log.txt")
    assert st.wall_s == 3.5 and st.peak_gpu_mem_mb == 1500.0 and st.cpu_s == 2.5


def test_host_stats_used_when_omr_run_wrote_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(containers, "run_monitored", lambda *a, **k: RunStats(wall_s=1.0, exit_code=125))
    st = containers.run_in_container("img", ["x"], workdir=tmp_path, log_path=tmp_path / "l.txt")
    assert st.exit_code == 125


def test_timeout_kills_the_named_container(tmp_path, monkeypatch):
    killed = []
    monkeypatch.setattr(containers, "run_monitored", lambda *a, **k: RunStats(timed_out=True))
    monkeypatch.setattr(containers, "kill", killed.append)
    containers.run_in_container("img", ["x"], workdir=tmp_path, log_path=tmp_path / "l.txt")
    assert len(killed) == 1 and killed[0].startswith("omrbench-")


def test_omr_run_writes_stats_for_a_command(tmp_path):
    out = subprocess.run(
        [sys.executable, str(ROOT / "docker" / "base" / "omr_run.py"),
         "--stats", str(tmp_path / "stats.json"), "--", sys.executable, "-c", "import time; time.sleep(0.3)"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    data = json.loads((tmp_path / "stats.json").read_text())
    assert data["exit_code"] == 0 and data["wall_s"] >= 0.3 and data["peak_rss_mb"] > 0
