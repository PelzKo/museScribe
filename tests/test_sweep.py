import json
from pathlib import Path

import pytest

from omrbench import bench as bench_mod
from omrbench import sweep
from omrbench import transcribe as transcribe_mod
from omrbench.project import Part


def test_several_output_parts_for_one_truth_part_are_overlaid():
    part = Part("1", "Keyboard 1", Path("k.pdf"), {}, ["Keyboard 1"])
    mapping, unmapped, problems = bench_mod.resolve(part, [("Piano", None), ("Synth", None)])
    assert mapping == {"Keyboard 1": ["Piano", "Synth"]} and not unmapped and not problems


class PowerCut(BaseException):
    """Not caught by the sweep's per-engine `except Exception`, like a crash."""


def test_resume_skips_finished_engines(tmp_path, monkeypatch):
    cfg = {"results_dir": str(tmp_path), "data_dir": str(tmp_path),
           "engines": {"a": {"type": "pipeline"}, "b": {"type": "pipeline"}}}
    calls, crashed = [], []
    monkeypatch.setattr(sweep, "_truth_songs", lambda cfg, show, songs: ["1"])
    monkeypatch.setattr(sweep, "report", lambda *a, **k: None)
    monkeypatch.setattr(sweep, "_docker_up", lambda: True)

    def fake_transcribe(cfg, **kw):
        calls.append(("t", kw["engine"]))
        if kw["engine"] == "b" and not crashed:
            crashed.append(1)
            raise PowerCut                # the PC dies in the middle of engine b
        return 0
    monkeypatch.setattr(transcribe_mod, "transcribe", fake_transcribe)
    monkeypatch.setattr(bench_mod, "bench", lambda cfg, show, **kw: calls.append(("b", kw["run"])))

    sweep.save_plan(cfg, "s", {"shows": ["x"], "engines": ["a", "b"], "grids": [], "songs": None,
                               "full": False, "jobs": None})
    with pytest.raises(PowerCut):
        sweep.sweep(cfg, ["x"], ["a", "b"], sweep_id="s")
    status = json.loads((tmp_path / "sweeps" / "s" / "status.json").read_text())
    assert status == {"x/a": {"ok": True, "failed_pdfs": 0, "s": 0}}
    calls.clear()
    plan = sweep.load_plan(cfg, "s")
    sweep.sweep(cfg, plan["shows"], plan["engines"], sweep_id="s", resume=True)
    assert calls == [("t", "b"), ("b", "s-b")]          # a is not redone
    calls.clear()
    sweep.sweep(cfg, plan["shows"], plan["engines"], sweep_id="s", rebench=True)
    assert calls == [("b", "s-a"), ("b", "s-b")]        # re-score only


def test_grid_variants_come_back_on_resume(tmp_path):
    cfg = {"results_dir": str(tmp_path), "engines": {"pipeline": {"type": "pipeline"}}}
    names = sweep.grid_engines(cfg, "pipeline", "recognizer=homr,clarity")
    sweep.save_plan(cfg, "g", {"shows": ["x"], "engines": names,
                               "grids": [{"base": "pipeline", "grid": "recognizer=homr,clarity"}]})
    fresh = {"results_dir": str(tmp_path), "engines": {"pipeline": {"type": "pipeline"}}}
    assert sweep.load_plan(fresh, "g")["engines"] == names
    assert fresh["engines"]["pipeline+recognizer-clarity"]["recognizer"] == "clarity"


def test_no_docker_stops_the_sweep_without_marking_engines_failed(tmp_path, monkeypatch):
    cfg = {"results_dir": str(tmp_path), "engines": {"a": {}}}
    monkeypatch.setattr(sweep, "_truth_songs", lambda cfg, show, songs: ["1"])
    monkeypatch.setattr(sweep, "_docker_up", lambda: False)
    with pytest.raises(SystemExit, match="resume"):
        sweep.sweep(cfg, ["x"], ["a"], sweep_id="d")
    assert not (tmp_path / "sweeps" / "d" / "status.json").exists()
