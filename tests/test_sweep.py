import json
from pathlib import Path

import pytest

from omrbench import bench as bench_mod
from omrbench import sweep
from omrbench.metrics import notef1
from omrbench import transcribe as transcribe_mod
from omrbench.project import Part


def test_several_output_parts_for_one_truth_part_are_overlaid():
    part = Part("1", "Keyboard 1", Path("k.pdf"), {}, ["Keyboard 1"])
    mapping, unmapped, problems = bench_mod.resolve(part, [("Piano", None), ("Synth", None)])
    assert mapping == {"Keyboard 1": ["Piano", "Synth"]} and not unmapped and not problems


def test_one_output_part_can_feed_two_truth_parts():
    part = Part("1", "PianoReduction", Path("p.pdf"), {}, ["Oda Mae=Voice 1", "Oda Mae=Voice 2", "Piano=Klavier"])
    mapping, unmapped, _ = bench_mod.resolve(part, [("Oda Mae", None), ("Piano", None), ("Sam", None)])
    assert mapping == {"Voice 1": ["Oda Mae"], "Voice 2": ["Oda Mae"], "Klavier": ["Piano"]}
    assert unmapped == ["Sam"]


def test_repeated_page_engine_part_names_are_numbered():
    assert bench_mod._unique([("Voice", 1), ("", 2), ("voice", 3)]) == [("Voice", 1), ("", 2), ("voice #2", 3)]


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
    calls.clear()
    status = json.loads((tmp_path / "sweeps" / "s" / "status.json").read_text())
    status["x/a"]["failed_pdfs"] = 1
    (tmp_path / "sweeps" / "s" / "status.json").write_text(json.dumps(status))
    sweep.sweep(cfg, plan["shows"], plan["engines"], sweep_id="s", resume=True)
    assert calls == [("t", "a"), ("b", "s-a")]          # failed PDFs are retried on resume


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


def test_report_leaves_piano_reductions_out_for_page_engines(tmp_path):
    cfg = {"results_dir": str(tmp_path), "engines": {"pipeline": {"type": "pipeline"}, "homr": {"type": "homr"}}}

    def row(part, pen, split=False):
        m = notef1.prf(1, 1, 1)
        return {"song": "1", "part": part, "truth": part, "split": split, "metrics": {"notes": m, "aligned": m},
                "edits": {"penalty": pen, "from_scratch": 100, "bars_to_fix": 0, "shift": 0, "by_cat": {"notes": pen}}}
    sys_ = {"penalty": 0, "from_scratch": 0, "by_cat": {}}
    for e, rows in {"pipeline": [row("Violin", 10), row("PianoReduction", 50, True)],
                    "homr": [row("Violin", 20), row("PianoReduction", 100, True)]}.items():
        d = tmp_path / "x" / "bench" / f"s-{e}"
        d.mkdir(parents=True)
        (d / "scores.json").write_text(json.dumps({"rows": rows, "songs": [{"song": "1", "system": sys_}]}))
    text = sweep.report(cfg, ["x"], ["pipeline", "homr"], "s").read_text()
    assert "| 1 | pipeline | **10** |" in text and "| 2 | homr | **20** |" in text
