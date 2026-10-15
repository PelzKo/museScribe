# oemer 0.1.8 with the pins from setup.sh: onnxruntime >=1.20 rejects its model (negative
# ConvTranspose pads), numpy 2 / OpenCV 4.10 change HoughLinesP output.
# onnxruntime-gpu 1.19 is the CUDA 12 build and falls back to CPU without a GPU.
# Build context is the repo root (`omrbench images build oemer`).
ARG BASE_IMAGE=omrbench/base:cuda
FROM ${BASE_IMAGE}

ARG OEMER_VERSION=0.1.8

RUN python3 -m venv /opt/oemer \
 && /opt/oemer/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/oemer/bin/pip install --no-cache-dir "oemer==${OEMER_VERSION}" \
      "numpy<2" "opencv-python-headless==4.8.1.78" "scipy<1.14" "scikit-learn<1.6" \
 && /opt/oemer/bin/pip uninstall -y onnxruntime onnxruntime-gpu opencv-python || true \
 && /opt/oemer/bin/pip install --no-cache-dir --no-deps "onnxruntime-gpu==1.19.2" \
 && /opt/oemer/bin/pip install --no-cache-dir --no-deps --force-reinstall "opencv-python-headless==4.8.1.78"

# checkpoints at build time (same logic as oemer.ete.main), so runs are not timed with a download
RUN /opt/oemer/bin/python - <<'PY'
import os
from oemer import ete
for title, url in ete.CHECKPOINTS_URL.items():
    save_dir = os.path.join(ete.MODULE_PATH, "checkpoints",
                            "unet_big" if title.startswith("1st") else "seg_net")
    ete.download_file(title, url, os.path.join(save_dir, title.split("_")[1]))
assert os.path.exists(os.path.join(ete.MODULE_PATH, "checkpoints/unet_big/model.onnx"))
PY

# oemer always asks for CUDAExecutionProvider; onnxruntime-gpu 1.19 segfaults on that without a GPU.
# device: cpu sets CUDA_VISIBLE_DEVICES="", so then ask for CPU only.
RUN /opt/oemer/bin/python - <<'PY'
import oemer.inference as m
p = m.__file__
s = open(p).read()
old = '        if sys.platform == "darwin":\n'
assert s.count(old) == 1
s = s.replace(old, '        if os.environ.get("CUDA_VISIBLE_DEVICES") == "":\n'
                   '            providers = ["CPUExecutionProvider"]\n'
                   '        elif sys.platform == "darwin":\n')
open(p, "w").write(s)
PY

ENV PATH=/opt/oemer/bin:$PATH
ENTRYPOINT []
