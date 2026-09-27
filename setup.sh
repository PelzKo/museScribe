#!/usr/bin/env bash
# Install the OMR benchmark harness and all engines into Linux-native dirs (WSL).
# Venvs on /mnt/c are slow and break symlinks, so everything lives under $OMRBENCH_HOME.
#
# Usage: bash setup.sh [--gpu] [--skip-audiveris] [--skip-homr] [--skip-oemer]
set -euo pipefail

OMRBENCH_HOME="${OMRBENCH_HOME:-$HOME/.local/share/omrbench}"
AUDIVERIS_VERSION="${AUDIVERIS_VERSION:-5.11.0}"
TESS_LANGS="${TESS_LANGS:-deu lat eng ita}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GPU=0; SKIP_AUD=0; SKIP_HOMR=0; SKIP_OEMER=0
for arg in "$@"; do
  case "$arg" in
    --gpu) GPU=1 ;;
    --skip-audiveris) SKIP_AUD=1 ;;
    --skip-homr) SKIP_HOMR=1 ;;
    --skip-oemer) SKIP_OEMER=1 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

mkdir -p "$OMRBENCH_HOME"/{venvs,tools,downloads}
echo "==> OMRBENCH_HOME=$OMRBENCH_HOME"

need() { command -v "$1" >/dev/null || { echo "missing '$1' ($2)"; exit 1; }; }
need python3 "sudo apt install python3 python3-venv"
need curl "sudo apt install curl"
need dpkg-deb "part of dpkg"
python3 -c "import ensurepip" 2>/dev/null || { echo "missing python3-venv (sudo apt install python3-venv)"; exit 1; }

mkvenv() {  # mkvenv <name> <pip args...>
  local name="$1"; shift
  local v="$OMRBENCH_HOME/venvs/$name"
  [ -x "$v/bin/python" ] || python3 -m venv "$v"
  "$v/bin/pip" install -q --upgrade pip
  "$v/bin/pip" install -q "$@"
  echo "    venv $name ready"
}

# ---------------------------------------------------------------- harness
echo "==> harness venv"
mkvenv harness -r "$REPO_DIR/requirements.txt"
"$OMRBENCH_HOME/venvs/harness/bin/pip" install -q -e "$REPO_DIR"

# ---------------------------------------------------------------- Audiveris
if [ "$SKIP_AUD" = 0 ]; then
  echo "==> Audiveris $AUDIVERIS_VERSION"
  . /etc/os-release
  case "$VERSION_ID" in 22.04|24.04) UBU="$VERSION_ID" ;; *) UBU=24.04 ;; esac
  DEB="Audiveris-${AUDIVERIS_VERSION}-ubuntu${UBU}-x86_64.deb"
  DEB_PATH="$OMRBENCH_HOME/downloads/$DEB"
  [ -f "$DEB_PATH" ] || curl -fL --retry 3 -o "$DEB_PATH" \
    "https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/${DEB}"
  AUD_DIR="$OMRBENCH_HOME/tools/audiveris-$AUDIVERIS_VERSION"
  if [ ! -d "$AUD_DIR" ]; then
    # extract without root; the .deb bundles its own JRE under opt/audiveris
    dpkg-deb -x "$DEB_PATH" "$AUD_DIR"
  fi
  AUD_BIN="$(find "$AUD_DIR" -type f -path '*/bin/Audiveris' | head -1)"
  [ -n "$AUD_BIN" ] || { echo "Audiveris launcher not found in $AUD_DIR"; exit 1; }
  ln -sf "$AUD_BIN" "$OMRBENCH_HOME/tools/audiveris"
  echo "    launcher: $AUD_BIN"

  echo "==> Tesseract language data: $TESS_LANGS"
  TESS_DIR="$OMRBENCH_HOME/tools/tessdata"
  mkdir -p "$TESS_DIR"
  for l in $TESS_LANGS; do
    [ -f "$TESS_DIR/$l.traineddata" ] || curl -fsSL --retry 3 -o "$TESS_DIR/$l.traineddata" \
      "https://github.com/tesseract-ocr/tessdata/raw/main/$l.traineddata"
  done
fi

# ---------------------------------------------------------------- homr
if [ "$SKIP_HOMR" = 0 ]; then
  echo "==> homr"
  mkvenv homr homr psutil
  if [ "$GPU" = 1 ]; then
    "$OMRBENCH_HOME/venvs/homr/bin/pip" uninstall -q -y onnxruntime || true
    "$OMRBENCH_HOME/venvs/homr/bin/pip" install -q --force-reinstall --no-deps onnxruntime-gpu
  fi
  # download models now so the first benchmark run isn't timed with a download
  "$OMRBENCH_HOME/venvs/homr/bin/homr" --init >/dev/null 2>&1
  echo "    homr models ready"
fi

# ---------------------------------------------------------------- oemer
if [ "$SKIP_OEMER" = 0 ]; then
  echo "==> oemer"
  # oemer 0.1.8 (2024) breaks on current wheels: onnxruntime >=1.20 rejects its model
  # (negative ConvTranspose pads) and numpy 2 / OpenCV 4.10 change HoughLinesP output.
  OEMER_PINS=("numpy<2" "opencv-python-headless==4.8.1.78" "scipy<1.14" "scikit-learn<1.6")
  mkvenv oemer oemer "${OEMER_PINS[@]}"
  "$OMRBENCH_HOME/venvs/oemer/bin/pip" uninstall -q -y onnxruntime onnxruntime-gpu || true
  if [ "$GPU" = 1 ]; then
    "$OMRBENCH_HOME/venvs/oemer/bin/pip" install -q --no-deps "onnxruntime-gpu==1.19.2"
  else
    "$OMRBENCH_HOME/venvs/oemer/bin/pip" install -q --no-deps "onnxruntime==1.19.2"
  fi
  # oemer downloads its checkpoints on first use; do it now (same logic as oemer.ete.main)
  "$OMRBENCH_HOME/venvs/oemer/bin/python" - >/dev/null <<'PY'
import os
from oemer import ete
if not os.path.exists(os.path.join(ete.MODULE_PATH, "checkpoints/unet_big/model.onnx")):
    for title, url in ete.CHECKPOINTS_URL.items():
        save_dir = os.path.join(ete.MODULE_PATH, "checkpoints",
                                "unet_big" if title.startswith("1st") else "seg_net")
        ete.download_file(title, url, os.path.join(save_dir, title.split("_")[1]))
PY
  echo "    oemer checkpoints ready"
fi

cat > "$OMRBENCH_HOME/env.sh" <<EOF
export OMRBENCH_HOME="$OMRBENCH_HOME"
export PATH="$OMRBENCH_HOME/venvs/harness/bin:\$PATH"
EOF

echo
echo "Done. Activate with:  source $OMRBENCH_HOME/env.sh"
echo "Then:                 omrbench doctor"
