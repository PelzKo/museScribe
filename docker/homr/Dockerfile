# homr, pinned like setup.sh, on onnxruntime-gpu (CUDA 12 build; Turing/RTX 2070 SUPER runs fp16/fp32, no bf16).
# Build context is the repo root; the worker is the same file the native homr pool uses.
ARG BASE_IMAGE=omrbench/base:cuda
FROM ${BASE_IMAGE}

ARG HOMR_VERSION=0.7.0

RUN python3 -m venv /opt/homr \
 && /opt/homr/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/homr/bin/pip install --no-cache-dir "homr==${HOMR_VERSION}" psutil \
 && /opt/homr/bin/pip uninstall -y onnxruntime \
 && /opt/homr/bin/pip install --no-cache-dir onnxruntime-gpu \
 && /opt/homr/bin/homr --init

COPY omrbench/engines/_homr_worker.py /opt/homr/worker.py

ENV PATH=/opt/homr/bin:$PATH
ENTRYPOINT []
