#!/bin/bash
# =============================================================================
# run.sh — I1 U7 admission-failure matrix + listener behavior regression
# =============================================================================
#
# Drives the admission-gate harness (`solum:digestio` + `solum:hauri` →
# `gradus:model/gguf` admit) across the five-failure fixture matrix
# and asserts the D5 process exit contract for the harness paths:
#
#   exit 0 — admission succeeded; the verified whole-file SHA-256 is printed.
#   exit 2 — admission failed; the typed cause is printed.
#
# The failure fixtures are prepared locally by fixtures.py from the pinned row
# (byte-identical copies with a single patch each — never committed) and each
# must fail with its own typed faber-runtime AdmissionError cause:
#
#   malformed        -> invalid GGUF magic             (InvalidMagic)
#   wrong-arch       -> architecture "qwen2"           (ArchitectureMismatch)
#   wrong-quant      -> F32 tensor count 64 != 65      (PerTypeTensorCountMismatch)
#   digest-mismatch  -> SHA-256 mismatch               (Sha256Mismatch)
#   unknown-key      -> unknown metadata key           (UnknownMetadataKey)
#
# No weight materialization is possible on this path: the harness only ever
# calls `gguf.admit` (never generate), so each
# fixture rejection happens before any allocation proportional to the row.
#
# The listener regression then starts the PRODUCT binary on the malformed
# fixture and asserts the server still serves /health (200, failed state with
# the typed cause in the body) after admission failure — the listener must
# survive an admission rejection.
#
# Usage: ./run.sh [MODEL_PATH]
#   MODEL_PATH defaults to the pinned SmolLM2-360M row. PORT overrides the
#   listener-regression port (default 18107).
# =============================================================================
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATE="$ROOT/tests/admission-gate"
BIN="$GATE/target/debug/admission-gate"
SERVER="$ROOT/target/debug/inferentia"
MODEL="${1:-/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf}"
PORT="${PORT:-18107}"

# Compiler contract (see README "Current commands"): the package imports
# `gradus:`/`norma:` providers, so the build needs the container as
# FABER_LIBRARY_HOME and the workspace radix binary — the PATH `faber` lags
# main and fails package resolution (PKG001).
CONTAINER="$(cd "$ROOT/.." && pwd)"
FABER_LIBRARY_HOME="${FABER_LIBRARY_HOME:-$CONTAINER}"
export FABER_LIBRARY_HOME
FABER_BIN="${FABER_BIN:-$CONTAINER/radix/target/debug/faber}"
if [ ! -x "$FABER_BIN" ]; then
    note "BLOCKED: workspace faber binary not found: $FABER_BIN (set FABER_BIN)"
    exit 1
fi

PASS=0
FAIL=0

note() { printf '%s\n' "$*"; }
ok()   { printf 'PASS %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL %s\n' "$*"; FAIL=$((FAIL + 1)); }

# --- Harness binary ---------------------------------------------------------
if [ ! -x "$BIN" ]; then
    note "== building admission-gate harness (workspace faber + FABER_LIBRARY_HOME) =="
    (cd "$GATE" && "$FABER_BIN" build "$GATE") >/dev/null || {
        note "BLOCKED: admission-gate harness build failed (workspace faber build $GATE; see README \"Current commands\")"
        exit 1
    }
fi
if [ ! -x "$BIN" ]; then
    note "BLOCKED: $BIN still missing after build"
    exit 1
fi

# --- Fixture prep (tmpdir; never committed) --------------------------------
WORK="$(mktemp -d "${TMPDIR:-/tmp}/admission-gate-u7.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
note "== preparing the five-failure fixture matrix =="
python3 "$GATE/fixtures.py" "$MODEL" "$WORK" || {
    note "BLOCKED: fixture prep failed"
    exit 1
}

# --- Failure matrix: each fixture -> exit 2 + typed cause -------------------
note ""
note "== failure matrix: typed cause + exit 2 per fixture =="
while IFS=$'\t' read -r FIXTURE EXPECTED; do
    [ -n "$FIXTURE" ] || continue
    OUT="$("$BIN" "$FIXTURE" 2>&1)"
    STATUS=$?
    NAME="$(basename "$FIXTURE" .gguf)"
    if [ "$STATUS" -eq 2 ] && printf '%s\n' "$OUT" | grep -qF "$EXPECTED" \
        && printf '%s\n' "$OUT" | grep -qF "rejected:"; then
        ok "$NAME -> exit 2 + typed cause ('$EXPECTED')"
    else
        bad "$NAME expected exit 2 + '$EXPECTED', observed status $STATUS: $OUT"
    fi
done < "$WORK/manifest.tsv"

# --- Positive control: pinned row -> exit 0 + pinned SHA-256 ----------------
note ""
note "== positive control: pinned row -> exit 0 + pinned SHA-256 =="
OUT="$("$BIN" "$MODEL" 2>&1)"
STATUS=$?
if [ "$STATUS" -eq 0 ] && printf '%s\n' "$OUT" | grep -qF "admitted: 2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"; then
    ok "pinned row admitted (exit 0, verified whole-file SHA-256)"
else
    bad "positive control expected exit 0 + pinned SHA-256, observed status $STATUS: $OUT"
fi

# --- Listener regression: server still serves after admission failure -------
note ""
note "== listener regression: server still serves after admission failure =="
if [ ! -x "$SERVER" ]; then
    bad "server binary not built (build at the repo root per README \"Current commands\" first)"
else
    MALFORMED="$(awk -F'\t' 'NR==1{print $1}' "$WORK/manifest.tsv")"
    "$SERVER" serve --model "$MALFORMED" --port "$PORT" \
        >"$WORK/listener.log" 2>&1 &
    SERVER_PID=$!
    FAILED=0
    for _ in $(seq 1 30); do
        if grep -q "admission failed" "$WORK/listener.log" 2>/dev/null; then
            FAILED=1
            break
        fi
        sleep 1
    done
    if [ "$FAILED" -ne 1 ]; then
        kill -9 "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        bad "server did not report admission failure (see $WORK/listener.log)"
    else
        BODY1="$(curl -s "http://127.0.0.1:$PORT/health")"
        CODE1="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health")"
        BODY2="$(curl -s "http://127.0.0.1:$PORT/health")"
        if [ "$CODE1" = "200" ] \
            && printf '%s\n' "$BODY1" | grep -q '"state":"failed"' \
            && printf '%s\n' "$BODY1" | grep -qF "invalid GGUF magic" \
            && [ "$BODY1" = "$BODY2" ]; then
            ok "listener still serves /health (200, failed state, typed cause) after admission failure"
        else
            bad "listener health after admission failure: code=$CODE1 body=$BODY1 second=$BODY2"
        fi
        kill -TERM "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
    fi
fi

note ""
note "admission-failure matrix: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
