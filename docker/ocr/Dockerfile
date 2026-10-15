# OCR engines for the bar-number component benchmark (P6): EasyOCR (Apache-2.0) and docTR (Apache-2.0),
# on the Clarity image (CUDA torch already there). Models are downloaded at build time.
# Build context is the repo root (`omrbench images build ocr`).
ARG BASE_IMAGE=omrbench/clarity:c6bb8a4
FROM ${BASE_IMAGE}

ARG EASYOCR_VERSION=1.7.2
ARG DOCTR_VERSION=0.11.0
RUN /opt/clarity/venv/bin/pip install --no-cache-dir "easyocr==${EASYOCR_VERSION}" "python-doctr[torch]==${DOCTR_VERSION}"
ENV DOCTR_CACHE_DIR=/opt/ocr/doctr
RUN mkdir -p /opt/ocr/easyocr /opt/ocr/doctr \
 && /opt/clarity/venv/bin/python -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='/opt/ocr/easyocr')" \
 && /opt/clarity/venv/bin/python -c "from doctr.models import ocr_predictor; ocr_predictor(pretrained=True)" \
 && chmod -R a+rX /opt/ocr
COPY --chmod=755 docker/ocr/words.py /opt/ocr/words.py
RUN printf '#!/bin/sh\nexec /opt/clarity/venv/bin/python /opt/ocr/words.py "$@"\n' > /usr/local/bin/ocr-words \
 && chmod +x /usr/local/bin/ocr-words
ENTRYPOINT []
