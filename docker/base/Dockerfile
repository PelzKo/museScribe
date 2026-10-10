# Shared base: Ubuntu 24.04 (same as the WSL host), Python venv with the in-container monitor.
# Build context is the repo root (see omrbench/containers.py build_cmd); `omrbench images build` runs it.
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/monitor \
 && /opt/monitor/bin/pip install --no-cache-dir psutil pynvml

COPY docker/base/omr_run.py /opt/monitor/omr_run.py
RUN printf '#!/bin/sh\nexec /opt/monitor/bin/python /opt/monitor/omr_run.py "$@"\n' > /usr/local/bin/omr-run \
 && chmod +x /usr/local/bin/omr-run

WORKDIR /work
