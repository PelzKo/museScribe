# homr, pinned like setup.sh, on onnxruntime-gpu (CUDA 12 build; Turing/RTX 2070 SUPER runs fp16/fp32, no bf16).
# Build: docker build -t omrbench/homr:0.7.0 --build-arg BASE_IMAGE=omrbench/base:cuda docker/homr
ARG BASE_IMAGE=omrbench/base:cuda
FROM ${BASE_IMAGE}

ARG HOMR_VERSION=0.7.0

RUN python3 -m venv /opt/homr \
 && /opt/homr/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/homr/bin/pip install --no-cache-dir "homr==${HOMR_VERSION}" psutil \
 && /opt/homr/bin/pip uninstall -y onnxruntime \
 && /opt/homr/bin/pip install --no-cache-dir onnxruntime-gpu \
 && /opt/homr/bin/homr --init

ENV PATH=/opt/homr/bin:$PATH
ENTRYPOINT []
