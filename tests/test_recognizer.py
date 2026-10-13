import pytest

from omrbench.pipeline import assemble as A
from omrbench.pipeline import recognizer as R


def test_vote_labels_crop_source():
    assert A._vote(4, [5, 5]) == (5, "crop")
    assert A._vote(4, [4, 4]) == (4, "agree")
    assert A._vote(4, [5]) == (5, "crop")   # tie: crop counts win, plan_systems may overrule


def test_unknown_recognizer():
    with pytest.raises(ValueError, match="known: homr"):
        R.build("pipeline", {"recognizer": "nope"}, {})


def test_kern_recognizer_falls_back_to_homr(tmp_path):
    rec = R.build("pipeline", {"recognizer": "smt-sys"}, {"home": str(tmp_path)})
    assert rec.name == "smt-sys+homr" and rec.main.staves == {2}


def test_fallback_routes_by_group_size(tmp_path):
    class Fake:
        def __init__(self, name):
            self.name, self.seen = name, []

        def recognize(self, jobs, *a):
            self.seen += jobs
            return [(j, None if self.name == "main" else "x") for j in jobs]

    main, fb = Fake("main"), Fake("fb")
    main.staves = {2}
    jobs = [(0, 0, 1, "a"), (0, 1, 2, "b"), (1, 0, 2, "c")]
    out = R.WithFallback(main, fb).recognize(jobs, tmp_path, tmp_path / "log", None, 1)
    assert out == [(jobs[0], "x"), (jobs[1], None), (jobs[2], None)]
    assert fb.seen == [jobs[0]]


def test_zeus_one_call_per_staff_count(tmp_path):
    rec = R.build("pipeline", {"recognizer": "zeus"}, {"home": str(tmp_path)}).main
    jobs = [(0, 0, 2, tmp_path / "a.png"), (0, 1, 1, tmp_path / "b.png"), (1, 0, 2, tmp_path / "c.png")]
    calls = rec.commands(jobs, tmp_path)
    assert [[j[3].name for j in part] for part, _ in calls] == [["b.png"], ["a.png", "c.png"]]
    assert calls[0][1][3] == "/opt/zeus/models/solo.model" and calls[1][1][3] == "/opt/zeus/models/grand.model"


def test_engine_device_override(tmp_path):
    bench = {"home": str(tmp_path), "device": "cuda"}
    homr = R.build("pipeline", {}, bench).engine
    assert homr.device == "cpu" and homr.env()["CUDA_VISIBLE_DEVICES"] == ""   # homr: CPU by default
    assert R.build("pipeline", {"homr": {"device": "cuda"}}, bench).engine.device == "cuda"
    assert R.build("pipeline", {"recognizer": "zeus"}, bench).main.engine.device == "cuda"


def test_plan_systems_raw_keeps_crop_bars():
    from omrbench.pipeline import bars as B
    from omrbench.pipeline.layout import Page, Stack, Staff, System
    staff = Staff(id=1, part=0, top=100, bottom=140, left=0, right=1000)
    sy = System(page=1, id=1, staves=[staff], stacks=[Stack(i, i * 250, (i + 1) * 250) for i in range(4)])
    page = Page(number=1, width=1200, height=1600, systems=[sy])
    D = 4
    aud = {(0, 0): [B.rest_bar(1, 4 * D, D) for _ in range(4)]}
    crop = {(0, 0): [B.rest_bar(1, 4 * D, D) for _ in range(7)]}
    stats = A.Stats()
    plan = A.plan_systems([page], aud, crop, D, ["crop", "audiveris"], stats, raw=True)[0]
    assert plan.n == 7 and stats.bars["crop"] == 7
    stats = A.Stats()
    plan = A.plan_systems([page], aud, {}, D, ["crop", "audiveris"], stats, raw=True)[0]
    assert plan.n == 4 and stats.bars["audiveris"] == 4   # crop failed: Audiveris bars


def test_bar_similarity():
    from omrbench.pipeline import bars as B
    a = B.rest_bar(1, 16, 4)
    assert B.similarity(B.signature(a), B.signature(a)) == 1.0   # rests only: both empty
