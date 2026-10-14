#!/usr/bin/env bash
# Iteratively discover SPU functions the lifter missed (reached only through
# runtime-built function pointers / vtables) for one image, by running the port
# and harvesting "branched into unlifted LS" / "BRANCH-TO-0 unresolved pc=" lines.
#
# Usage: scripts/spu_discover.sh <image-name> <image-id> <agent> [max-iters] [run-seconds]
#   e.g. scripts/spu_discover.sh spu_0001_at_00B61480 2 claude 12 50
# Requires the LIFT lock (work/spu/lifted) held by <agent>.
set -u
IMG="$1"; IID="$2"; AGENT="$3"; MAX="${4:-12}"; SECS="${5:-50}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/Scripts/python"
LIST="$ROOT/work/spu/${IMG}_extra.txt"
touch "$LIST"
export PYTHONUTF8=1

for i in $(seq 1 "$MAX"); do
  echo "=== iteration $i: extra=$(cat "$LIST")"
  (cd "$ROOT/agents/$AGENT/ps3recomp" && "$PY" tools/build_spu_workloads.py \
      --images "$ROOT/work/spu/images" --lifted "$ROOT/work/spu/lifted" \
      --out "$ROOT/work/spu/lifted/spu_workloads.c" --register-fn port_spu_register_all \
      --constructor --title allstars --extra-funcs "$IMG=$(cat "$LIST")" --relift >/dev/null 2>&1) \
      || { echo "relift failed"; exit 1; }
  (cd "$ROOT" && cmd //c "scripts\\build.bat Release $AGENT") > "$ROOT/work/runs/disc-build-$i.log" 2>&1 \
      || { echo "build failed (see work/runs/disc-build-$i.log)"; exit 1; }
  powershell -ExecutionPolicy Bypass -File "$(cygpath -w "$ROOT/scripts/run.ps1")" \
      -Agent "$AGENT" -Seconds "$SECS" -Tag "disc-$IMG-$i" >/dev/null
  LOG="$ROOT/work/runs/disc-$IMG-$i.err.log"
  NEW=$( { grep -oE "img=$IID branched into unlifted LS 0x[0-9A-Fa-f]+" "$LOG" | grep -oE "0x[0-9A-Fa-f]+$";
           grep -oE "BRANCH-TO-0 unresolved pc=0x[0-9A-Fa-f]+ image=$IID" "$LOG" | grep -oE "pc=0x[0-9A-Fa-f]+" | cut -d= -f2;
           grep -oE "wws-jobentry\] pc=0x[0-9A-Fa-f]+" "$LOG" | cut -d= -f2; } \
         | tr 'a-f' 'A-F' | sed 's/^0X/0x/' | sort -u)
  ADDED=0
  for a in $NEW; do
    if ! tr ',' '\n' < "$LIST" | grep -qix "$a"; then
      if [ -s "$LIST" ]; then printf ',%s' "$a" >> "$LIST"; else printf '%s' "$a" >> "$LIST"; fi
      ADDED=1; echo "  + $a"
    fi
  done
  if [ "$ADDED" = 0 ]; then echo "no new unlifted targets -- done after $i iteration(s)"; exit 0; fi
done
echo "max iterations reached"
