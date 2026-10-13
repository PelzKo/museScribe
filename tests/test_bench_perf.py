import json

from omrbench import bench


def test_perf_from_manifest_or_run(tmp_path):
    root = tmp_path / "show"
    wd = root / "runs" / "r1" / "pipeline" / "show-1--Violin"
    wd.mkdir(parents=True)
    (wd / "result.json").write_text(json.dumps({"engine": "pipeline", "pages": 2, "stats": {
        "wall_s": 10.0, "cpu_user_s": 4.0, "cpu_sys_s": 1.0, "peak_rss_mb": 900.0, "peak_gpu_mem_mb": None}}))
    entry = {"run": "r1", "engine": "pipeline"}
    p = bench._perf(root, root, "show-1--Violin", entry)
    assert p["wall_s"] == 10.0 and p["cpu_s"] == 5.0 and p["pages"] == 2
    assert bench._perf(root, root / "runs" / "r1", "show-1--Violin", {})["engine"] == "pipeline"
    assert bench._perf(root, root, "show-1--Cello", {}) is None
