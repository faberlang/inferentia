#!/bin/bash
# =============================================================================
# process-exit — product-binary process-status integration check (I1 D5)
# =============================================================================
#
# Asserts the ACTUAL `$?` of the product binary `target/debug/inferentia`:
#
#   exit 0 — clean shutdown after successful admission
#   exit 2 — shutdown after failed admission
#
# The check is the D5 contract: `exit_code_for` (src/main.fab) is not just
# computed and printed — it must be DELIVERED to the process when the serve
# loop terminates. The loop ends when the listener is stopped (`http:stop`)
# or the accept is cancelled; the delivery route is `processus:exi`
# (`exit_with` in src/main.fab).
#
# STATUS AT THIS COMMIT: BLOCKED by two scoped toolchain gaps (see README):
#   (1) faber-runtime native-host dispatch does not deliver `processus:exi`
#       (plan-time classifies it as a builtin route; the installed NativeHost
#       shadows the builtin and rejects the route; the rejection path then
#       deadlocks). Scoped as the u2p1 runtime fix.
#   (2) no loop-end trigger is wired: SIGTERM kills the process (status 143)
#       because no signal handling exists (recorded U6 gap).
# Until those land, the product-binary assertions report the ACTUAL statuses
# as evidence (expected 0/2, observed 143) and exit 1.
#
# The admission path itself (real `model:admit` on the pinned row) is proven
# end-to-end by the admission-gate harness under tests/admission-gate/.
#
# Usage: ./run.sh [MODEL_PATH]
#   MODEL_PATH defaults to the pinned SmolLM2-360M row.
# =============================================================================
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="$ROOT/target/debug/inferentia"
MODEL="${1:-/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf}"
PORT="${PORT:-18099}"
PORT2="${PORT2:-18100}"

PASS=0
FAIL=0

note() { printf '%s\n' "$*"; }
ok()   { printf 'PASS %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL %s\n' "$*"; FAIL=$((FAIL + 1)); }

# --- Product binary: clean shutdown after successful admission -> exit 0 ---
note "== product binary: clean shutdown (valid model) -> exit 0 =="
if [ ! -x "$BIN" ]; then
    note "BLOCKED: $BIN not built (run: faber build .)"
else
    "$BIN" serve --model "$MODEL" --port "$PORT" \
        >"$ROOT/tests/process-exit/out-clean.log" 2>&1 &
    SERVER_PID=$!
    # Wait for the ready state (stderr: "model loaded once"). The generation
    # warm-up is one-time and can take ~2 min on a busy machine.
    READY=0
    for _ in $(seq 1 180); do
        if grep -q "generation ready" "$ROOT/tests/process-exit/out-clean.log" 2>/dev/null; then
            READY=1
            break
        fi
        sleep 1
    done
    if [ "$READY" -ne 1 ]; then
        kill -9 "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        bad "server did not reach ready (see out-clean.log); observed: $(cat "$ROOT/tests/process-exit/out-clean.log" 2>/dev/null | tail -2)"
    else
        note "server ready; terminating"
        kill -TERM "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID"
        STATUS=$?
        if [ "$STATUS" -eq 0 ]; then
            ok "clean shutdown exit 0 (observed $STATUS)"
        else
            bad "clean shutdown expected 0, observed $STATUS (SIGTERM without the U6 signal route kills the process; loop-end exit delivery blocked on the scoped faber-runtime fix)"
        fi
    fi
fi

# --- Product binary: failed admission -> exit 2 ---------------------------
note "== product binary: failed admission -> exit 2 =="
if [ ! -x "$BIN" ]; then
    note "BLOCKED: $BIN not built (run: faber build .)"
else
    "$BIN" serve --model "$ROOT/tests/process-exit/missing-model.gguf" --port "$PORT2" \
        >"$ROOT/tests/process-exit/out-failed.log" 2>&1 &
    SERVER_PID=$!
    FAILED=0
    for _ in $(seq 1 30); do
        if grep -q "admission failed" "$ROOT/tests/process-exit/out-failed.log" 2>/dev/null; then
            FAILED=1
            break
        fi
        sleep 1
    done
    if [ "$FAILED" -ne 1 ]; then
        kill -9 "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        bad "server did not report admission failure (see out-failed.log)"
    else
        note "failed health served; terminating"
        kill -TERM "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID"
        STATUS=$?
        if [ "$STATUS" -eq 2 ]; then
            ok "failed-admission exit 2 (observed $STATUS)"
        else
            bad "failed-admission expected 2, observed $STATUS (blocked as above)"
        fi
    fi
fi

note ""
note "product-binary process-status check: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
