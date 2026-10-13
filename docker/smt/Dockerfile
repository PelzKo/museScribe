# Sheet Music Transformer, full-page pianoform (MIT): page image -> bekern. Repo pinned to a commit, weights
# to a Hugging Face revision. PRAIG/smt-fp-mozarteum and -polish-scores are gated (need an HF token), so the
# default is smt-fp-grandstaff; smt-sys is the same image with the system-level PRAIG/smt-grandstaff. Versions from the repo's uv.lock; torch CUDA wheels on the CPU base.
# Build context is the repo root.
ARG BASE_IMAGE=omrbench/base:cpu
FROM ${BASE_IMAGE}

ARG SMT_COMMIT=20d8240c47b4a1851e9a5aa5a0ca3d0ddbc16da8
ENV HF_HOME=/opt/hf PYTHONPATH=/opt/smt/src

RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && git init -q /opt/smt/src \
 && git -C /opt/smt/src fetch -q --depth 1 https://github.com/antoniorv6/SMT.git "$SMT_COMMIT" \
 && git -C /opt/smt/src checkout -q FETCH_HEAD \
 && rm -rf /opt/smt/src/.git

RUN python3 -m venv /opt/smt/venv \
 && /opt/smt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/smt/venv/bin/pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
      --index-url https://download.pytorch.org/whl/cu126 \
 && /opt/smt/venv/bin/pip install --no-cache-dir transformers==4.49.0 loguru "numpy<2" pillow

# the model comes last, so the variants (smt-fp, smt-sys) share the layers above
ARG SMT_MODEL=PRAIG/smt-fp-grandstaff
ARG SMT_REVISION=6f8d5c093d218a71117ef51492efc2952adcc217
ENV SMT_MODEL=${SMT_MODEL} SMT_REVISION=${SMT_REVISION}
COPY docker/smt/adapter.py /opt/smt/adapter.py
RUN /opt/smt/venv/bin/python -c "\
import os; from smt_model import SMTModelForCausalLM as M; \
M.from_pretrained(os.environ['SMT_MODEL'], revision=os.environ['SMT_REVISION'])" \
 && chmod -R a+rX /opt/hf
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN printf '#!/bin/sh\nexec /opt/smt/venv/bin/python /opt/smt/adapter.py "$@"\n' > /usr/local/bin/smt \
 && chmod +x /usr/local/bin/smt
ENTRYPOINT []
