# Transcoda (AGPL code, CC-BY-4.0 weights): full-page pianoform image -> **kern, via the Hugging Face
# remote-code model (revision pinned: trust_remote_code runs that code). Torch CUDA wheels bundle their CUDA
# libs, so the CPU base works on both machines. Build context is the repo root.
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG TRANSCODA_REVISION=b529f8aa5d996d9224df3395b5b92d0867343c91
ENV TRANSCODA_REVISION=${TRANSCODA_REVISION} HF_HOME=/opt/hf

RUN python3 -m venv /opt/transcoda \
 && /opt/transcoda/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/transcoda/bin/pip install --no-cache-dir torch==2.9.1 torchvision==0.24.1 \
      --index-url https://download.pytorch.org/whl/cu126 \
 && /opt/transcoda/bin/pip install --no-cache-dir transformers==4.57.3 pillow numpy loguru torchtune==0.6.1 torchao==0.15.0

COPY docker/transcoda/adapter.py /opt/transcoda/adapter.py
# fetch weights, remote code and the ConvNeXt-V2 encoder config now; offline at run time
RUN /opt/transcoda/bin/python -c "\
import os; from transformers import AutoModelForCausalLM as M, PreTrainedTokenizerFast as T; \
r = os.environ['TRANSCODA_REVISION']; R = 'btrkeks/transcoda-59M-zeroshot-v1'; \
M.from_pretrained(R, revision=r, trust_remote_code=True); T.from_pretrained(R, revision=r)" \
 && chmod -R a+rX /opt/hf
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN printf '#!/bin/sh\nexec /opt/transcoda/bin/python /opt/transcoda/adapter.py "$@"\n' > /usr/local/bin/transcoda \
 && chmod +x /usr/local/bin/transcoda
ENTRYPOINT []
