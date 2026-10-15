# Zeus (OmniOMR/zeus, MIT code): one staff or grand staff per image -> MusicXML (via LMX). TensorFlow 2.12
# needs Python 3.10 and CUDA 11.8 / cuDNN 8, hence the base-cuda11 image (Ubuntu 22.04). Models, checked
# by sha256: zeus-olimpic-1.0 (grand staves, CC BY-SA) and ayce-2026-08-03 (solo staves, CC BY-NC-SA).
# Build context is the repo root.
ARG BASE_IMAGE=omrbench/base:cuda11
FROM ${BASE_IMAGE}

ARG ZEUS_COMMIT=c8569eb1c8b5bb24511de6a5e53ef2450de6206c
RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/zeus/venv \
 && /opt/zeus/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/zeus/venv/bin/pip install --no-cache-dir "zeus @ git+https://github.com/OmniOMR/zeus.git@${ZEUS_COMMIT}"

RUN mkdir -p /opt/zeus/models && cd /opt/zeus/models \
 && curl -fsSLo grand.tgz https://github.com/ufal/olimpic-icdar24/releases/download/zeus-release/zeus-olimpic-1.0-2024-02-12.model.tar.gz \
 && curl -fsSLo solo.tgz https://github.com/Jirka-Mayer/ijdar/releases/download/model-snapshots/ayce-2026-08-03.model.tar.gz \
 && printf '%s  grand.tgz\n%s  solo.tgz\n' \
      85f601cb7370175754c0cd9b2d4799f5a744c6d25e5e4f18705b08b79a0c54d2 \
      43ff26dc968d759b57385befe985b02ab7f891ee869cf399f5175c9b06028e1c | sha256sum -c - \
 && tar xzf grand.tgz && tar xzf solo.tgz && rm grand.tgz solo.tgz \
 && mv zeus-olimpic-1.0-2024-02-12.model grand.model && mv ayce-2026-08-03.model solo.model \
 && chmod -R a+rX /opt/zeus/models
RUN ln -s /opt/zeus/venv/bin/zeus /usr/local/bin/zeus
ENTRYPOINT []
