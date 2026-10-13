# OLA (v-dvorak/omr-layout-analysis, MIT): YOLOv8 layout model for systems, staves, grand staves,
# system measures and staff measures. The Clarity image already has Ultralytics and CUDA torch.
# Build context is the repo root (`omrbench images build ola`).
ARG BASE_IMAGE=omrbench/clarity:c6bb8a4
FROM ${BASE_IMAGE}

ARG OLA_RELEASE=ola-v2.0
ARG OLA_WEIGHTS=ola-layout-analysis-2.0-2025-03-09.pt
ADD --chmod=644 https://github.com/v-dvorak/omr-layout-analysis/releases/download/${OLA_RELEASE}/${OLA_WEIGHTS} /opt/ola/model.pt
COPY --chmod=755 docker/ola/predict.py /opt/ola/predict.py
RUN chmod 755 /opt/ola
RUN printf '#!/bin/sh\nexec /opt/clarity/venv/bin/python /opt/ola/predict.py "$@"\n' > /usr/local/bin/ola \
 && chmod +x /usr/local/bin/ola
ENV YOLO_CONFIG_DIR=/tmp/ultralytics
ENTRYPOINT []
