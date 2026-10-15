# Clarity-OMR (GPL-3 code, CC-BY-SA weights): YOLO staff detection + DaViT token model, PDF -> MusicXML.
# The repo has no releases: pinned to a commit. Torch CUDA wheels bundle their CUDA libs, so the CPU base
# works on both machines (GPU via --gpus all). Build context is the repo root (`omrbench images build clarity`).
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG CLARITY_COMMIT=c6bb8a4d2a5b52842a9c41bd0f761f58d02f6f82
ARG TORCH_VERSION=2.7.1
ARG TORCHVISION_VERSION=0.22.1

# git to fetch the commit; libgl/glib for ultralytics' OpenCV
RUN apt-get update \
 && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0t64 \
 && rm -rf /var/lib/apt/lists/*

RUN git init -q /opt/clarity \
 && git -C /opt/clarity fetch -q --depth 1 https://github.com/clquwu/Clarity-OMR.git "$CLARITY_COMMIT" \
 && git -C /opt/clarity checkout -q FETCH_HEAD \
 && rm -rf /opt/clarity/.git

RUN python3 -m venv /opt/clarity/venv \
 && /opt/clarity/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/clarity/venv/bin/pip install --no-cache-dir "torch==${TORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}" \
      --index-url https://download.pytorch.org/whl/cu126 \
 && /opt/clarity/venv/bin/pip install --no-cache-dir -r /opt/clarity/requirements.txt

# shortcut: weights are HF main at build time (no revision pin); pin a revision if they change under us
RUN cd /opt/clarity && /opt/clarity/venv/bin/python -c "\
from pathlib import Path; from src.model_assets import *; r = Path('.'); \
print(ensure_default_stage_a_weights(r), ensure_default_stage_b_checkpoint(r))"

# the DaViT backbone's ImageNet weights are replaced by the checkpoint: don't download them at run time.
# Ultralytics writes its settings to YOLO_CONFIG_DIR (HOME is /tmp in our containers anyway).
ENV OMR_DISABLE_BACKBONE_PRETRAINED=1 YOLO_CONFIG_DIR=/tmp/ultralytics
RUN printf '#!/bin/sh\ncd /opt/clarity && exec /opt/clarity/venv/bin/python omr.py "$@"\n' > /usr/local/bin/clarity \
 && chmod +x /usr/local/bin/clarity
COPY docker/clarity/crops.py /opt/clarity/crops.py
RUN printf '#!/bin/sh\nexec /opt/clarity/venv/bin/python /opt/clarity/crops.py "$@"\n' > /usr/local/bin/clarity-crops \
 && chmod +x /usr/local/bin/clarity-crops
ENTRYPOINT []
