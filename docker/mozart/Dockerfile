# Mozart (Apache-2.0): classic-CV OMR (staff removal, HOG + MLP symbol classifier), one treble staff at a time.
# Its classifier is a scikit-learn 0.23 pickle, so Python 3.8 and the 2020 stack from its requirements.yml.
# Build context is the repo root.
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG MOZART_COMMIT=a51c9d767f37fa5e8c0968f2c9282edbdd8d08fe

RUN apt-get update \
 && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0t64 \
 && rm -rf /var/lib/apt/lists/* \
 && git init -q /opt/mozart \
 && git -C /opt/mozart fetch -q --depth 1 https://github.com/aashrafh/Mozart.git "$MOZART_COMMIT" \
 && git -C /opt/mozart checkout -q FETCH_HEAD \
 && rm -rf /opt/mozart/.git /opt/mozart/output /opt/mozart/testcases

ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN python3 -m venv /opt/uv && /opt/uv/bin/pip install --no-cache-dir uv \
 && /opt/uv/bin/uv venv --python 3.8 /opt/mozart/venv \
 && /opt/uv/bin/uv pip install --python /opt/mozart/venv/bin/python --no-cache \
      numpy==1.19.4 scipy==1.5.3 scikit-learn==0.23.2 scikit-image==0.17.2 \
      opencv-python-headless==4.5.1.48 imutils==0.5.3 matplotlib==3.3.3 pillow==8.0.1 \
 && chmod -R a+rX /opt/uv-python

# adapter contract (`mozart --out DIR [--device X] PAGE...`) over Mozart's folder-in, folder-out CLI
ENV MPLBACKEND=Agg
RUN printf '%s\n' '#!/bin/sh' \
      'out=""; while [ $# -gt 0 ]; do case "$1" in --out) out="$2"; shift 2;; --device) shift 2;; *) break;; esac; done' \
      'in=$(mktemp -d); for f in "$@"; do ln -s "$f" "$in/"; done' \
      'cd /opt/mozart/src && exec /opt/mozart/venv/bin/python main.py "$in" "$out"' > /usr/local/bin/mozart \
 && chmod +x /usr/local/bin/mozart
ENTRYPOINT []
