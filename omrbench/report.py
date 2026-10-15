"""Render results/<run>/report.md from manifest.json, scores.json and engine results."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from . import dataset
from .musicxml import CATEGORIES

LOWER_BETTER = "↓"
HIGHER_BETTER = "↑"


def _pct(x, digits=1):
    return "–" if x is None else f"{100 * x:.{digits}f}%"


def _num(x, digits=1):
    return "–" if x is None else f"{x:,.{digits}f}"


def _table(headers: list[str], rows: list[list], best: dict[int, str] | None = None,
           raw: list[list] | None = None) -> str:
    """Markdown table; `best` maps column index -> 'min'|'max' to bold the winner."""
    rows = [list(r) for r in rows]
    if best and raw:
        for c, how in best.items():
            vals = [(r[c], i) for i, r in enumerate(raw) if isinstance(r[c], (int, float))]
            if len(vals) > 1:
                target = (min if how == "min" else max)(v for v, _ in vals)
                for v, i in vals:
                    if v == target:
                        rows[i][c] = f"**{rows[i][c]}**"
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" if i == 0 else "---:" for i in range(len(headers))) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else None


class Data:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.manifest = json.loads((run_dir / "manifest.json").read_text())
        sp = run_dir / "scores.json"
        self.scores: dict = json.loads(sp.read_text()) if sp.exists() else {}
        self.results = {}
        for p in sorted(run_dir.glob("*/*/result.json")):
            r = json.loads(p.read_text())
            self.results[(r["engine"], r["sample"])] = r
        cfg = self.manifest["config"]
        # re-read samples so meta edits made after the run are picked up
        try:
            samples, _ = dataset.discover(Path(cfg.get("samples_dir", cfg["data_dir"])), None,
                                          cfg.get("musescore_cli"), cache=dataset.cache_dir(cfg))
            self.samples = {s.id: s for s in samples}
        except Exception:
            self.samples = {}
        self.sample_ids = [s["id"] for s in self.manifest["samples"]]
        self.meta = {s["id"]: (self.samples[s["id"]].meta if s["id"] in self.samples else s["meta"])
                     for s in self.manifest["samples"]}
        self.pdfkind = {s["id"]: s.get("pdfkind") for s in self.manifest["samples"]}   # older runs: none
        eng_order = list(self.manifest["engines"])
        self.engines = [e for e in eng_order if any(k[0] == e for k in self.results)]
        self.variants = list((cfg.get("scoring") or {}).get("omr_ned_variants") or {"all": 1})

    def samples_of(self, eng: str) -> list[str]:
        return [s for s in self.sample_ids if (eng, s) in self.results]

    def sc(self, eng, sid) -> dict:
        return (self.scores.get(eng) or {}).get(sid) or {}

    def failed(self, eng, sid) -> bool:
        r = self.results.get((eng, sid))
        return r is None or r.get("error") is not None or not self.sc(eng, sid)

    # --- metric accessors, failures penalised (NED/TEDn = 1, F1 = 0) -----------
    def ned(self, eng, sid, variant):
        if self.failed(eng, sid):
            return 1.0
        d = (self.sc(eng, sid).get("omr_ned") or {}).get(variant)
        return d["omr_ned"] if d else None

    def tedn(self, eng, sid):
        if self.failed(eng, sid):
            return 1.0
        d = self.sc(eng, sid).get("tedn")
        return min(d["tedn"], 1.0) if d and d.get("tedn") is not None else None

    def elem(self, eng, sid, cat, key="f1"):
        if self.failed(eng, sid):
            return 0.0 if key in ("f1", "recall") else None
        d = (self.sc(eng, sid).get("elements") or {}).get(cat)
        return d.get(key) if d else None

    def pooled_elem(self, eng, sids, cat) -> dict:
        tp = n_pred = n_gt = 0
        for s in sids:
            d = (self.sc(eng, s).get("elements") or {}).get(cat)
            if d:
                tp += d["tp"]; n_pred += d["pred"]; n_gt += d["gt"]
            elif not self.failed(eng, s):
                continue
            else:  # failed: everything in GT missed
                gt_d = next(((self.sc(e, s).get("elements") or {}).get(cat)
                             for e in self.engines if (self.sc(e, s).get("elements") or {}).get(cat)),
                            None)
                n_gt += gt_d["gt"] if gt_d else 0
        p = tp / n_pred if n_pred else None
        r = tp / n_gt if n_gt else None
        f = (2 * p * r / (p + r) if p and r else 0.0) if p is not None and r is not None else None
        return {"precision": p, "recall": r, "f1": f, "gt": n_gt, "pred": n_pred}

    def mer(self, eng, sid):
        if self.failed(eng, sid):
            return 1.0
        return (self.sc(eng, sid).get("measures") or {}).get("measure_error_rate")

    def stats(self, eng, sid) -> dict | None:
        r = self.results.get((eng, sid))
        return r.get("stats") if r else None

    def pages(self, sid) -> int:
        for (e, s), r in self.results.items():
            if s == sid and r.get("pages"):
                return r["pages"]
        return 0


def _sum_row(d: Data, eng: str, sids: list[str]) -> tuple[list, list]:
    ok = [s for s in sids if not d.failed(eng, s)]
    have = [s for s in sids if (eng, s) in d.results]
    neds = [_mean(d.ned(eng, s, v) for s in have) for v in d.variants]
    ted = _mean(d.tedn(eng, s) for s in have)
    nf1 = d.pooled_elem(eng, have, "notes")["f1"]
    mer = _mean(d.mer(eng, s) for s in have)
    # failed runs are fast and small; leave them out of the resource columns
    st = [d.stats(eng, s) for s in ok if d.stats(eng, s)]
    pages = sum(d.pages(s) for s in ok if d.stats(eng, s)) or None
    wall = sum(x["wall_s"] for x in st) / pages if st and pages else None
    cpu = sum(x["cpu_s"] for x in st) / pages if st and pages else None
    rss = max((x["peak_rss_mb"] for x in st), default=None)
    gpu = max((x["peak_gpu_mem_mb"] for x in st if x.get("peak_gpu_mem_mb") is not None), default=None)
    raw = [eng, f"{len(ok)}/{len(sids)}", *neds, ted, nf1, mer, wall, cpu, rss, gpu]
    fmt = [f"`{eng}`", raw[1], *[_pct(x) for x in neds], _pct(ted), _pct(nf1), _pct(mer),
           _num(wall), _num(cpu), _num(rss, 0), _num(gpu, 0)]
    return fmt, raw


def _summary_table(d: Data, sids: list[str], engines: list[str]) -> str:
    headers = ["Engine", "OK", *[f"OMR-NED {v} {LOWER_BETTER}" for v in d.variants],
               f"TEDn {LOWER_BETTER}", f"Note F1 {HIGHER_BETTER}", f"Measure err {LOWER_BETTER}",
               "Wall s/page", "CPU s/page", "Peak RAM MB", "Peak GPU MB"]
    rows, raws = [], []
    for e in engines:
        if not any((e, s) in d.results for s in sids):
            continue
        f, r = _sum_row(d, e, sids)
        rows.append(f)
        raws.append(r)
    n = len(d.variants)
    best = {2 + i: "min" for i in range(n)}
    best.update({2 + n: "min", 3 + n: "max", 4 + n: "min", 5 + n: "min", 6 + n: "min", 7 + n: "min"})
    return _table(headers, rows, best, raws)


def write_report(run_dir: Path) -> Path:
    d = Data(run_dir)
    m = d.manifest
    host = m.get("host", {})
    cfg = m["config"]
    L: list[str] = []
    A = L.append

    A(f"# OMR benchmark report — run `{m['run_id']}`\n")
    A(f"Generated {datetime.now():%Y-%m-%d %H:%M}. Started {m.get('started', '?')}. "
      f"{len(d.sample_ids)} samples, {len(d.engines)} engines.\n")
    A("**How to read:** ↓ lower is better, ↑ higher is better; best value per column in bold. "
      "Failed runs count as OMR-NED/TEDn/measure error = 100% and F1 = 0.\n")

    # ------------------------------------------------------------------ setup
    A("## Setup\n")
    gpus = ", ".join(f"{g['name']} ({g['mem_gb']} GB)" for g in host.get("gpus", [])) or "none visible"
    A(f"- **Host:** {host.get('cpu', '?')}, {host.get('cores_physical')}C/{host.get('cores_logical')}T, "
      f"{host.get('ram_gb')} GB RAM, GPU: {gpus}; {host.get('platform', '')}")
    A(f"- **Settings:** device `{cfg.get('device')}`, rasterisation {cfg.get('dpi')} dpi, "
      f"timeout {cfg.get('timeout_s')} s")
    A("")
    rows = []
    for name, e in m["engines"].items():
        extra = []
        c = e.get("config") or {}
        if c.get("use_metadata"):
            extra.append("switches from meta.yaml")
        if c.get("constants"):
            extra.append(f"constants: {c['constants']}")
        if e["type"] == "pipeline":
            extra.append(f"audiveris (meta.yaml switches) layout + homr per staff group; "
                         f"prefer {c.get('prefer', 'auto')}, text at {c.get('text_onset', 'bar')}")
        rows.append([f"`{name}`", e["type"], e["version"] if e["available"] else f"UNAVAILABLE: {e['version']}",
                     "; ".join(extra) or "defaults"])
    A(_table(["Engine", "Type", "Version", "Options"], rows))
    A("")

    # ------------------------------------------------------------------ dataset
    A("## Dataset\n")
    rows = []
    for sid in d.sample_ids:
        meta = d.meta.get(sid, {})
        c = next((d.sc(e, sid).get("counts") for e in d.engines if d.sc(e, sid).get("counts")), {}) or {}
        notes_gt = next(((d.sc(e, sid).get("elements") or {}).get("notes", {}).get("gt")
                         for e in d.engines if d.sc(e, sid).get("elements")), None)
        lyr_gt = next(((d.sc(e, sid).get("elements") or {}).get("lyrics", {}).get("gt")
                       for e in d.engines if d.sc(e, sid).get("elements")), None)
        rows.append([sid, meta.get("type", "other"), d.pdfkind.get(sid) or "?", d.pages(sid) or "?", c.get("gt_parts", "?"),
                     c.get("gt_staves", "?"), c.get("gt_measures", "?"), notes_gt or "?", lyr_gt or 0,
                     meta.get("source") or meta.get("notes") or ""])
    A(_table(["Sample", "Type", "PDF", "Pages", "Parts", "Staves", "Measures", "Notes", "Syllables", "Source"],
             rows))
    A("")

    # ------------------------------------------------------------------ summary
    A("## Overall ranking\n")
    A("Means over samples (F1 pooled over all tokens). Runtime per page, memory = peak over samples.\n")
    A(_summary_table(d, d.sample_ids, d.engines))
    A("")

    # ------------------------------------------------------------------ by type
    types = defaultdict(list)
    for sid in d.sample_ids:
        types[d.meta.get(sid, {}).get("type", "other")].append(sid)
    A("## By score type\n")
    for t, sids in types.items():
        A(f"### {t} ({', '.join(sids)})\n")
        A(_summary_table(d, sids, d.engines))
        A("")

    # ------------------------------------------------------------------ per sample
    A("## Per sample\n")
    for v in d.variants:
        A(f"**OMR-NED ({v})** {LOWER_BETTER}\n")
        rows, raws = [], []
        for e in d.engines:
            vals = [d.ned(e, s, v) if (e, s) in d.results else None for s in d.sample_ids]
            raws.append([e, *vals])
            rows.append([f"`{e}`", *[("FAIL" if (e, s) in d.results and d.failed(e, s) else _pct(x))
                                     for x, s in zip(vals, d.sample_ids)]])
        # bold per sample column = best engine for that sample
        A(_table(["Engine", *d.sample_ids], rows, {i + 1: "min" for i in range(len(d.sample_ids))}, raws))
        A("")
    A("**Structure** (output / GT). Extra parts usually mean the engine split one instrument, "
      "e.g. Audiveris opens a new part when the OCR'd part label changes between systems.\n")
    rows = []
    for e in d.engines:
        cells = []
        for s in d.sample_ids:
            c = d.sc(e, s).get("counts")
            if not c:
                cells.append("FAIL" if (e, s) in d.results else "–")
                continue
            def cmp(a, b):
                return f"{a}/{b}" if a == b else f"**{a}**/{b}"
            cells.append(f"parts {cmp(c['pred_parts'], c['gt_parts'])}, staves "
                         f"{cmp(c['pred_staves'], c['gt_staves'])}, bars {cmp(c['pred_measures'], c['gt_measures'])}")
        rows.append([f"`{e}`", *cells])
    A(_table(["Engine", *d.sample_ids], rows))
    A("")
    A(f"**TEDn** {LOWER_BETTER} (capped at 100%)\n")
    rows, raws = [], []
    for e in d.engines:
        vals = [d.tedn(e, s) if (e, s) in d.results else None for s in d.sample_ids]
        raws.append([e, *vals])
        rows.append([f"`{e}`", *[_pct(x) for x in vals]])
    A(_table(["Engine", *d.sample_ids], rows, {i + 1: "min" for i in range(len(d.sample_ids))}, raws))
    A("")

    # ------------------------------------------------------------------ elements
    A("## Per-element F1\n")
    A("Pooled over all samples; `–` = element absent from both GT and output. "
      "Precision/recall in the detail table below.\n")
    cats = [c for c in CATEGORIES
            if any(d.pooled_elem(e, d.samples_of(e), c)["gt"] or d.pooled_elem(e, d.samples_of(e), c)["pred"]
                   for e in d.engines)]
    rows, raws = [], []
    for e in d.engines:
        vals = [d.pooled_elem(e, d.samples_of(e), c)["f1"] for c in cats]
        raws.append([e, *vals])
        rows.append([f"`{e}`", *[_pct(x, 0) for x in vals]])
    A(_table(["Engine", *cats], rows, {i + 1: "max" for i in range(len(cats))}, raws))
    A("")
    A("<details><summary>Precision / recall per element and engine</summary>\n")
    rows = []
    for e in d.engines:
        for c in cats:
            pe = d.pooled_elem(e, d.samples_of(e), c)
            rows.append([f"`{e}`", c, pe["gt"], pe["pred"], _pct(pe["precision"]), _pct(pe["recall"]),
                         _pct(pe["f1"])])
    A(_table(["Engine", "Element", "GT", "Output", "Precision", "Recall", "F1"], rows))
    A("\n</details>\n")

    # ------------------------------------------------------------------ musicdiff breakdown
    A("## Where the edits are (musicdiff, OMR-NED `%s`)\n" % d.variants[0])
    A("Sum of OMR edit distance by symbol category over all samples — what you would have to fix.\n")
    per_eng = {}
    allcats = defaultdict(int)
    for e in d.engines:
        acc = defaultdict(int)
        for s in d.samples_of(e):
            bc = ((d.sc(e, s).get("omr_ned") or {}).get(d.variants[0]) or {}).get("by_category") or {}
            for k, v in bc.items():
                acc[k] += v
                allcats[k] += v
        per_eng[e] = acc
    top = [k for k, _ in sorted(allcats.items(), key=lambda kv: -kv[1])][:14]
    if top:
        rows = [[f"`{e}`", *[per_eng[e].get(k, 0) for k in top]] for e in d.engines]
        A(_table(["Engine", *[k.replace(" OMR-ED", "") for k in top]], rows))
    A("")

    # ------------------------------------------------------------------ flags
    A("## Uncertainty flags vs. real errors\n")
    A("Unit = one measure of one staff. *Erroneous* = measure content (notes/rests with onsets) "
      "not matching the aligned GT measure. A good flag source has high recall at a low flag rate.\n")
    rows = []
    for e in d.engines:
        have = [s for s in d.samples_of(e) if not d.failed(e, s)]
        if not have:
            continue
        me = [d.sc(e, s).get("measures") or {} for s in have]
        err = sum(x.get("erroneous_pred_units", 0) for x in me)
        units = sum(x.get("pred_units", 0) for x in me)
        srcs = sorted({k for s in have for k in (d.sc(e, s).get("flags") or {})})
        for src in srcs:
            tp = sum(((d.sc(e, s).get("flags") or {}).get(src) or {}).get("tp", 0) for s in have)
            fl = sum(((d.sc(e, s).get("flags") or {}).get(src) or {}).get("pred", 0) for s in have)
            p = tp / fl if fl else None
            r = tp / err if err else None
            f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
            rows.append([f"`{e}`", src, _pct(err / units if units else None), fl, _pct(fl / units if units else None),
                         _pct(p), _pct(r), _pct(f)])
    A(_table(["Engine", "Flag source", "Measures wrong", "Flagged", "Flag rate", "Precision", "Recall", "F1"],
             rows))
    A("")

    # ------------------------------------------------------------------ resources
    A("## Runtime and resources\n")
    A("Wall = elapsed time incl. model loading (homr/oemer: summed over one call per page; "
      "rasterisation reported separately). CPU = user+sys over the whole process tree; "
      "CPU util > 100% means multi-core. RAM = peak summed RSS of the process tree.\n")
    rows = []
    for e in d.engines:
        for s in d.samples_of(e):
            st = d.stats(e, s)
            if not st:
                continue
            r = d.results[(e, s)]
            pg = r.get("pages") or 1
            name = f"`{e}`" + (" (failed)" if d.failed(e, s) else "")
            rows.append([name, s, pg, _num(st["wall_s"]), _num(st["wall_s"] / pg), _num(st["cpu_s"]),
                         _num(st["avg_cpu_util_pct"], 0) + "%", _num(st["peak_rss_mb"], 0),
                         _num(st.get("peak_gpu_mem_mb"), 0), _num(r.get("prep_s"), 1),
                         _num(d.sc(e, s).get("scoring_s"), 0)])
    A(_table(["Engine", "Sample", "Pages", "Wall s", "Wall s/page", "CPU s", "CPU util", "Peak RAM MB",
              "Peak GPU MB", "Raster s", "Scoring s"], rows))
    A("")

    # ------------------------------------------------------------------ recommendation
    A("## Best engine per score type\n")
    rows = []
    for t, sids in types.items():
        cands = [e for e in d.engines if all((e, s) in d.results for s in sids)]
        if not cands:
            continue
        v = d.variants[0]
        best_ned = min(cands, key=lambda e: _mean(d.ned(e, s, v) for s in sids) or 9)
        best_notes = min(cands, key=lambda e: _mean(d.ned(e, s, d.variants[-1]) for s in sids) or 9)
        best_fast = min((e for e in cands
                         if all(d.stats(e, s) and not d.failed(e, s) for s in sids)),
                        key=lambda e: sum(d.stats(e, s)["wall_s"] for s in sids), default=None)
        rows.append([t, f"`{best_ned}` ({_pct(_mean(d.ned(best_ned, s, v) for s in sids))})",
                     f"`{best_notes}` ({_pct(_mean(d.ned(best_notes, s, d.variants[-1]) for s in sids))})",
                     f"`{best_fast}`" if best_fast else "–"])
    A(_table(["Type", f"Lowest OMR-NED {d.variants[0]}", f"Lowest OMR-NED {d.variants[-1]}", "Fastest"], rows))
    A("")

    # ------------------------------------------------------------------ failures
    fails = [(e, s, r.get("error")) for (e, s), r in d.results.items() if r.get("error")]
    serr = [(e, s, k, v) for e, per in d.scores.items() for s, sc in per.items()
            for k, v in (sc.get("errors") or {}).items() if k != "engine"]
    warn = [(e, s, f"{k}: {r['extras'][k]}") for (e, s), r in d.results.items()
            for k in ("failed_pages", "warning")
            if k in (r.get("extras") or {}) and not r.get("error")]
    for (e, s_), r in d.results.items():
        st = r.get("stats") or {}
        wc, wm = st.get("wall_clock_s") or 0, st.get("wall_s") or 0
        if wm and wc > 1.1 * wm + 5:
            warn.append((e, s_, f"clock time {wc:.0f}s vs monotonic {wm:.0f}s: machine/WSL VM was "
                                 "suspended or paused during the run; wall numbers exclude the pause"))
    if fails or serr or warn or m.get("warnings"):
        A("## Failures and warnings\n")
        for e, s, err in fails:
            A(f"- **{e} / {s}** engine: {err} (log: `{Path(e) / s / 'engine.log'}`)")
        for e, s, k, v in serr:
            A(f"- **{e} / {s}** metric `{k}`: {str(v).splitlines()[0][:300]}")
        for e, s, w in warn:
            A(f"- {e} / {s}: {w}")
        for w in m.get("warnings", []):
            A(f"- dataset: {w}")
        A("")

    # ------------------------------------------------------------------ method
    A("## Metrics\n")
    A("- **OMR-NED** (musicdiff): symbolic edit distance / (GT symbols + output symbols). "
      "`all` compares every notated object (notes, beams, articulations, slurs, signatures, directions, "
      "lyrics, ...); `notes` only notes and rests. 20% ≈ one in five symbols needs an edit.")
    A("- **TEDn** (OLiMPiC implementation of Hajič et al. 2016): tree edit distance on MusicXML "
      "with notes flattened, normalised by GT size. Large parts are scored measure-by-measure after "
      "aligning measures (`mode` in scores.json).")
    A("- **Per-element F1**: per staff, tokens of each element type in musical order; matches = longest "
      "common subsequence, so a dropped bar only costs its own content. Notes = pitch + duration; lyrics "
      "= verse + syllable text; words = lower-cased `<words>` text.")
    A("- **Measure error**: share of output measures (per staff) whose note/rest content differs from "
      "the aligned GT measure. Basis for flag precision/recall.")
    A("- **Flags**: `validator` = voice duration ≠ time signature (engine-agnostic); `audiveris` = "
      "abnormal measures / excess stacks from the `.omr` project; `combined` = union.")
    A("- **Resources**: sampled every 0.1 s with psutil over the whole process tree; GPU via NVML "
      "(device memory delta when per-process info is hidden, e.g. under WSL).")
    A("")
    A(f"Raw data: `scores.json`, `metrics.csv`, per-run folders `<engine>/<sample>/` with "
      "`output.musicxml` and `engine.log`.")

    out = run_dir / "report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
