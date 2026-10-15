# homr, pinned like setup.sh, on onnxruntime-gpu (1.31 is a CUDA 13 build: base-cuda13; with the CUDA 12 base its
# CUDA provider fails to load and homr silently runs its fp16 models on the CPU). Turing: fp16/fp32, no bf16.
# Build context is the repo root; the worker is the same file the native homr pool uses.
ARG BASE_IMAGE=omrbench/base:cuda13
FROM ${BASE_IMAGE}

ARG HOMR_VERSION=0.7.0
ARG ORT_VERSION=1.31.0

# both model sets: fp16 for CUDA (--init) and fp32 for CPU (--init --gpu no); the package dir is read-only at run time
RUN python3 -m venv /opt/homr \
 && /opt/homr/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/homr/bin/pip install --no-cache-dir "homr==${HOMR_VERSION}" psutil \
 && /opt/homr/bin/pip uninstall -y onnxruntime \
 && /opt/homr/bin/pip install --no-cache-dir "onnxruntime-gpu==${ORT_VERSION}" \
 && /opt/homr/bin/homr --init \
 && /opt/homr/bin/homr --init --gpu no

COPY omrbench/engines/_homr_worker.py /opt/homr/worker.py

ENV PATH=/opt/homr/bin:$PATH
ENTRYPOINT []
