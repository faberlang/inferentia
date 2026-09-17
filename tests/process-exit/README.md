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

## Status at this commit — BLOCKED (U6 loop-end trigger)

The product-binary assertions cannot pass yet: the serve-loop end path —
where `exit_with` delivers the D5 code through `processus:exi` — is never
reached, because **no loop-end trigger is wired**. SIGTERM/SIGINT handling
(`http:stop` after signal) is the recorded U6 gap ("the native host has
no processus signal route"). Until it lands, SIGTERM kills the process by
signal: expected 0 (clean shutdown) / 2 (failed admission), observed 143.

An earlier version of this section attributed the blocked exit delivery to
a native-dispatch gap in the `faber-runtime` crate, fixed at a commit there.
That repo no longer exists and the fix commit resolves in no faberlang repo
(provider ruling 2615e6a9 remapped inferentia onto `gradus:*`). Whether the
recomposed runtime delivers the loop-end `processus:exi` call is unverified
until U6 provides the trigger — noted for the U6 owner.

Until then, `run.sh` reports the observed statuses as evidence and
exits 1. The **admission path itself** (real `gradus:model/gguf` admit on the pinned
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
