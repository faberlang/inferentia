# tests/process-exit — product-binary process-status integration check (I1 D5)

This gate asserts the **actual `$?` of the product binary**
`target/debug/inferentia`, not just the harness:

- `exit 0` — clean shutdown after successful admission.
- `exit 2` — shutdown after failed admission.

The D5 contract (i1-delivery.md §4.155–168) says `exit_code_for`
(`src/main.fab`) must be **delivered to the process** when the serve loop
terminates. The serve loop ends when the listener is stopped (`http:stop`)
or the accept is cancelled; `exit_with` (the `processus:exi` primitive) then
delivers the code. Before this unit the loop-end path only **printed** the
intended code and **panicked** (exit 101); `exit_code_for` was computed and
tested but never delivered. The panic was replaced by `exit_with`.

## Status at this commit — BLOCKED (scoped)

The product-binary assertions cannot pass yet. Two toolchain gaps, both
scoped in the u2p1 closeout:

1. **faber-runtime native-host dispatch does not deliver `processus:exi`.**
   Faber's plan-time classification (`faber/src/package/dispatch.rs`
   `is_builtin_ad_route`) treats `processus:exi` as a *builtin* route (no
   native host required) — the no-host harness builds
   (`tests/admission-gate`, `tests/generate-gate`) deliver real exit codes
   0/2 through it. But `start_host_dispatch` (`faber-runtime/src/frame.rs`)
   routes every non-`runtime:` route to the installed `NativeHost` when a
   `[target.rust] host = "native"` product exists, and the native kernel
   does not manifest `processus:exi` (host-providers processus manifest —
   deliberately unmanifested). `NativeHost::start` rejects the route with
   `host_unsupported_route`, and the rejection path **deadlocks**
   (`responses.reject_start_error` re-locks the sermo mutex held by
   `sermo_recv`). Net effect: `call 'processus:exi'` in a native product
   hangs instead of exiting.
   Fix scope: in `start_host_dispatch`, fall back to
   `BuiltinRuntimeDispatch` for routes the installed host does not support
   (or manifest `processus:exi` in host-providers processus), then rebuild
   the core-support snapshot + faber binary.
2. **No loop-end trigger is wired.** SIGTERM/SIGINT handling
   (`http:stop` after signal) is the recorded U6 gap ("the native host has
   no processus signal route"). Until then SIGTERM kills the process by
   signal (observed `$?` = 143) and the loop-end path is unreachable.

Until both land, `run.sh` reports the observed statuses as evidence and
exits 1. The **admission path itself** (real `model:admit` on the pinned
row → exit 0 / exit 2) is proven end-to-end by the harness under
`tests/admission-gate/`.

## Usage

```sh
faber build .
./run.sh                # uses the pinned SmolLM2-360M row
./run.sh /path/to/model # explicit model
```

`PORT` env overrides the default 18099; `PORT2` the second run's port
(default 18100).
