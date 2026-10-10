# Audiveris batch CLI with its bundled JRE, same release as setup.sh (no root needed on the host).
# Build context is the repo root (`omrbench images build audiveris`).
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG AUDIVERIS_VERSION=5.11.0
ARG TESS_LANGS="deu lat eng ita"

# libgtk-3: Audiveris loads it via JNA at startup (HiDPI probe), even in -batch mode
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl libgtk-3-0t64 \
 && rm -rf /var/lib/apt/lists/*

# the .deb bundles its own JRE under opt/audiveris; extract it instead of installing
RUN curl -fL --retry 3 -o /tmp/audiveris.deb \
      "https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/Audiveris-${AUDIVERIS_VERSION}-ubuntu24.04-x86_64.deb" \
 && dpkg-deb -x /tmp/audiveris.deb /opt/audiveris-root \
 && rm /tmp/audiveris.deb \
 && AUD_BIN="$(find /opt/audiveris-root -type f -path '*/bin/Audiveris' | head -1)" \
 && test -n "$AUD_BIN" \
 && ln -s "$AUD_BIN" /usr/local/bin/Audiveris

# tessdata baked in: the OCR languages must match what the native setup used
ENV TESSDATA_PREFIX=/opt/tessdata
RUN mkdir -p /opt/tessdata \
 && for l in $TESS_LANGS; do \
      curl -fsSL --retry 3 -o /opt/tessdata/$l.traineddata \
        "https://github.com/tesseract-ocr/tessdata/raw/main/$l.traineddata" || exit 1; \
    done

ENTRYPOINT []
