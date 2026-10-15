# PaddleOCR (Apache-2.0) for the bar-number component benchmark (P6), CPU build (strip pages are small).
# Same entry point as docker/ocr: `ocr-words --engine paddle`. Build context is the repo root.
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG PADDLE_VERSION=3.2.0
# 3.0.x pins pandas 1.5.3 (no Python 3.12 wheel)
ARG PADDLEOCR_VERSION=3.3.0
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0t64 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/paddle \
 && /opt/paddle/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/paddle/bin/pip install --no-cache-dir "paddlepaddle==${PADDLE_VERSION}" "paddleocr==${PADDLEOCR_VERSION}"
# models into the image (PaddleX caches under HOME; containers run with HOME=/tmp)
ENV PADDLE_PDX_CACHE_HOME=/opt/paddlex
RUN /opt/paddle/bin/python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)" \
 && chmod -R a+rX /opt/paddlex
COPY --chmod=755 docker/ocr/words.py /opt/ocr/words.py
RUN printf '#!/bin/sh\nexec /opt/paddle/bin/python /opt/ocr/words.py "$@"\n' > /usr/local/bin/ocr-words \
 && chmod +x /usr/local/bin/ocr-words
ENTRYPOINT []
