"""Score one engine output against the ground truth."""
from __future__ import annotations

import multiprocessing as mp
import traceback
from pathlib import Path

from . import musicxml
from .dataset import Sample
from .engines.base import EngineResult
from .metrics import elements, flags, omrned, tedn


def _child(conn, fn, args):
    try:
        conn.send(("ok", fn(*args)))
    except BaseException as e:  # noqa: BLE001 - report everything to the parent
        conn.send(("err", f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"))
    finally:
        conn.close()


def with_timeout(fn, *args, timeout: float):
    """Run fn(*args) in a forked process; raise TimeoutError / RuntimeError on failure."""
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_child, args=(child, fn, args), daemon=True)
    p.start()
    child.close()
    if not parent.poll(timeout):
        p.kill()
        p.join()
        raise TimeoutError(f"exceeded {timeout:.0f}s")
    status, val = parent.recv()
    p.join()
    if status == "err":
        raise RuntimeError(val)
    return val


def _normalise_pred(pred: Path) -> tuple[Path, list[int] | None]:
    """Expand single-measure multirests; returns (path to score, old->new measure map)."""
    root = musicxml.load(pred)
    index_map = musicxml.expand_multirests(root)
    if index_map is None:
        return pred, None
    out = pred.with_name(pred.stem + ".scored.musicxml")
    musicxml.write(root, out)
    return out, index_map


def _structural(pred_path: Path, gt_path: Path, omr: Path | None,
                index_map: list[int] | None = None) -> dict:
    pred_root = musicxml.load(pred_path)
    gt_root = musicxml.load(gt_path)
    ps, gs = musicxml.extract_staves(pred_root), musicxml.extract_staves(gt_root)
    pairs = elements.pair_staves(ps, gs)
    out = {
        "counts": {
            "pred_parts": len(pred_root.findall("part")), "gt_parts": len(gt_root.findall("part")),
            "pred_staves": len(ps), "gt_staves": len(gs),
            "pred_measures": musicxml.measure_count(pred_root),
            "gt_measures": musicxml.measure_count(gt_root),
        },
        "staff_pairs": [[ps[i].label if i is not None else None,
                         gs[j].label if j is not None else None] for i, j in pairs],
        "elements": elements.element_scores(ps, gs, pairs),
    }
    wrong, n_pred, ok_gt, n_gt = flags.measure_errors(ps, gs, pairs)
    out["measures"] = {
        "pred_units": n_pred, "gt_units": n_gt, "erroneous_pred_units": len(wrong),
        "measure_error_rate": len(wrong) / n_pred if n_pred else None,
        "gt_measures_exact": ok_gt / n_gt if n_gt else None,
    }
    fl = {"validator": flags.validator_flags(pred_root)}
    if omr is not None and Path(omr).exists():
        fl["audiveris"] = flags.audiveris_flags(Path(omr))
        if index_map:  # .omr counts measures before multirest expansion
            fl["audiveris"] = {(pi, index_map[mi] if mi < len(index_map) else mi): why
                               for (pi, mi), why in fl["audiveris"].items()}
        fl["combined"] = {**fl["validator"], **fl["audiveris"]}
    out["flags"] = {name: flags.flag_scores(f, ps, wrong) for name, f in fl.items()}
    out["flagged_measures"] = {name: sorted(f"{pi}:{mi + 1} {why}" for (pi, mi), why in f.items())
                               for name, f in fl.items()}
    return out


def _tedn(pred_path: Path, gt_path: Path, max_nodes: int) -> dict:
    return tedn.tedn(musicxml.load(pred_path), musicxml.load(gt_path), max_nodes=max_nodes)


def score(res: EngineResult, sample: Sample, cfg: dict) -> dict:
    sc = cfg.get("scoring", {})
    timeout = float(sc.get("metric_timeout_s", 900))
    out: dict = {"errors": {}}
    if res.output is None or not Path(res.output).exists():
        out["errors"]["engine"] = res.error or "no output"
        return out
    gt = sample.gt
    try:
        pred, index_map = _normalise_pred(Path(res.output))
    except Exception as e:
        out["errors"]["normalise"] = str(e)
        pred, index_map = Path(res.output), None
    if index_map:
        out["measures_added_by_multirest_expansion"] = (
            musicxml.measure_count(musicxml.load(pred)) - len(index_map))

    try:
        out.update(with_timeout(_structural, pred, gt, res.extras.get("omr"), index_map,
                                timeout=timeout))
    except Exception as e:
        out["errors"]["structural"] = str(e)

    out["omr_ned"] = {}
    for name, detail in (sc.get("omr_ned_variants") or {"all": "AllObjects"}).items():
        try:
            out["omr_ned"][name] = with_timeout(omrned.omr_ned, pred, gt, detail, timeout=timeout)
        except Exception as e:
            out["errors"][f"omr_ned[{name}]"] = str(e)

    if sc.get("tedn", True):
        try:
            out["tedn"] = with_timeout(_tedn, pred, gt, int(sc.get("tedn_max_nodes", 2500)),
                                       timeout=timeout)
        except Exception as e:
            out["errors"]["tedn"] = str(e)
    return out
