#!/usr/bin/env bash
# Smoke test for the containerised engines on the synthetic demo sample.
#   1. homr image sees the GPU (CUDAExecutionProvider); skipped without nvidia-smi
#   2. demo samples exist (creates them with `omrbench demo` if not)
#   3. audiveris and homr run in their containers on demo-violin-part
#   4. output files are owned by the calling user, not root
# Usage: bash scripts/smoke_docker.sh [SAMPLE]    (default SAMPLE: demo-violin-part)
set -uo pipefail
cd "$(dirname "$0")/.."
SAMPLE="${1:-demo-violin-part}"
fail=0
step() { echo; echo "==> $*"; }
ok()   { echo "    OK   $*"; }
bad()  { echo "    FAIL $*"; fail=1; }

step "1. homr image: onnxruntime providers"
if nvidia-smi -L >/dev/null 2>&1; then
  providers="$(docker run --rm --gpus all omrbench/homr:0.7.0 /opt/homr/bin/python \
    -c 'import onnxruntime as o; print(o.get_available_providers())' 2>&1)"
  echo "    $providers"
  if grep -q CUDAExecutionProvider <<<"$providers"; then ok "GPU provider available"; else bad "no CUDAExecutionProvider"; fi
else
  ok "no GPU on this machine, skipped (device auto -> cpu)"
fi

step "2. demo sample $SAMPLE"
if [ ! -f "data/samples/$SAMPLE/input.pdf" ]; then
  omrbench demo || { bad "omrbench demo failed"; exit 1; }
fi
[ -f "data/samples/$SAMPLE/input.pdf" ] && ok "$SAMPLE present" || { bad "$SAMPLE missing"; exit 1; }

step "3. audiveris + homr in containers on $SAMPLE"
omrbench run --engines audiveris,homr --samples "$SAMPLE" || bad "omrbench run exited non-zero"
run="$(ls -td results/samples/bench/*/ 2>/dev/null | head -1)"
if [ -z "$run" ]; then bad "no run directory produced"; exit 1; fi
echo "    run dir: $run"

step "4. outputs and ownership"
for eng in audiveris homr; do
  out="$run$eng/$SAMPLE/output.musicxml"
  if [ -s "$out" ]; then ok "$eng: $out"; else bad "$eng: no output.musicxml (see $run$eng/$SAMPLE/engine.log)"; fi
  [ -f "$run$eng/$SAMPLE/result.json" ] && ok "$eng result.json written" || bad "$eng: no result.json"
  # files the container wrote must belong to the calling user (container runs as host uid)
  roots="$(find "$run$eng/$SAMPLE" -user root 2>/dev/null | head -3)"
  if [ -z "$roots" ]; then ok "$eng: no root-owned files"; else bad "$eng: root-owned files, e.g. $roots"; fi
done

step "summary"
sed -n '1,25p' "${run}report.md" 2>/dev/null || true
if [ "$fail" = 0 ]; then echo; echo "SMOKE TEST PASSED"; else echo; echo "SMOKE TEST FAILED (see FAIL lines above)"; fi
exit "$fail"
