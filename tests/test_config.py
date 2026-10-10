from omrbench import config


def test_device_auto_and_gpu_only_skip(tmp_path, monkeypatch):
    y = tmp_path / "bench.yaml"
    y.write_text("engines:\n  audiveris: {type: audiveris}\n  big: {type: homr, requires_gpu: true}\n")
    monkeypatch.setattr(config, "has_gpu", lambda: False)
    cfg = config.load(y)
    assert cfg["device"] == "cpu"
    assert [e.name for e in config.engines(cfg)] == ["audiveris"]
    monkeypatch.setattr(config, "has_gpu", lambda: True)
    cfg = config.load(y)
    assert cfg["device"] == "cuda"
    assert [e.name for e in config.engines(cfg)] == ["audiveris", "big"]
