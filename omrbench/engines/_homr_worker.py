"""Persistent homr worker, run with the homr venv's python (no omrbench imports).

Loads homr once and transcribes one image per request, so the ~1-3 s of imports and
ONNX model loading per crop are paid once per worker. Same result as the `homr IMAGE`
CLI with default options.

Protocol: one JSON object per line. stdin  {"id": n, "image": path}
                                      stdout {"id": n, "ok": bool, "error": str, "log": str,
                                              "wall_s": f, "cpu_s": f, "rss_mb": f}
argv: intra-op threads per ONNX session (0 = onnxruntime default), niceness increment
"""
import io
import json
import os
import resource
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout

# the protocol owns the real stdout; anything homr prints goes to the per-task log
proto = os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1)
os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
threads = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if len(sys.argv) > 2 and int(sys.argv[2]):
    os.nice(int(sys.argv[2]))

import onnxruntime as ort  # noqa: E402

if threads:
    _session = ort.InferenceSession

    def _limited(*args, **kwargs):
        so = kwargs.get("sess_options")
        if so is None and len(args) > 1 and isinstance(args[1], ort.SessionOptions):
            so = args[1]
            args = args[:1] + args[2:]
        so = so or ort.SessionOptions()
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1
        kwargs["sess_options"] = so
        return _session(*args, **kwargs)

    ort.InferenceSession = _limited
    import cv2  # noqa: E402

    cv2.setNumThreads(threads)

from homr.main import (ProcessingConfig, XmlGeneratorArguments, cuda_available,  # noqa: E402
                       coreml_available, download_weights)

# onnxruntime-gpu lists CUDA even with no GPU; device: cpu hides the GPU with CUDA_VISIBLE_DEVICES=""
gpu = cuda_available() and os.environ.get("CUDA_VISIBLE_DEVICES") != ""
segnet_gpu = gpu or coreml_available()
download_weights(segnet_gpu, gpu, False)
ort.set_default_logger_severity(3)
CONFIG = ProcessingConfig(enable_debug=False, enable_cache=False, write_staff_positions=False,
                          read_staff_positions=False, selected_staff=-1, transformer_use_gpu=gpu,
                          segnet_use_gpu=segnet_gpu, coreml_encoder=False)
XML_ARGS = XmlGeneratorArguments(large_page=False, metronome=None, tempo=None)
from homr.main import process_image  # noqa: E402

proto.write(json.dumps({"ready": True, "gpu": gpu}) + "\n")
for line in sys.stdin:
    if not line.strip():
        continue
    req = json.loads(line)
    buf = io.StringIO()
    t0, c0 = time.perf_counter(), time.process_time()
    ok, err = True, ""
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            process_image(req["image"], CONFIG, XML_ARGS)
    except BaseException as e:  # noqa: BLE001 - reported to the caller
        ok, err = False, f"{type(e).__name__}: {e}"
        buf.write(traceback.format_exc())
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    proto.write(json.dumps({"id": req["id"], "ok": ok, "error": err, "log": buf.getvalue()[-20000:],
                            "wall_s": time.perf_counter() - t0, "cpu_s": time.process_time() - c0,
                            "rss_mb": rss}) + "\n")
