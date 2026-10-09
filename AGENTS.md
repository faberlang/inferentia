# Inferentia Agent Guide

**Workspace work mode.** Ordinary development is **direct** in this
checkout on `main`. Worktree packets under `../worktrees/<lane>/` are
optional Tugboat isolation. Do not stand up lanes unless the operator
asked. Container law: [`../AGENTS.md`](../AGENTS.md).

## Project

Inferentia is a separate Faber application product. It serves GGUF language
models through a local CLI and HTTP API.

Treat `faber.toml`, `README.md`, the campaign, and live source as the source of
truth. When they disagree, working code and observed behavior win.

## Ownership boundaries

- Keep product policy in this repository.
- Put reusable ML semantics in Gradus only when Inferentia proves the need.
- Put compiler and Faber build-tool work in private Radix.
- Put physical effects behind the appropriate Host provider.
- Do not move Inferentia commands into the generic Faber CLI or public Faber
  target API packages.
- Do not make `llama.cpp` a production dependency. It is a comparison oracle.
- Keep deployment and machine provisioning in a separate campaign.

## Development stance

- Use Faber for application and request-policy code.
- Fail closed on unsupported GGUF architecture, quantization, tokenizer, or
  metadata combinations.
- Prefer one verified model row before generalizing.
- Add a second caller or model row before extracting abstractions.
- Preserve foreign changes in every sibling repository.
- A campaign or goal is planning evidence, not proof that code shipped.

## Validation

Run the narrowest useful proof first — the package imports `gradus:` and
`norma:` providers, so compilation needs the container as
`FABER_LIBRARY_HOME`, the workspace radix binary (the PATH `faber` lags main
and fails package resolution with `PKG001`), and an absolute input path:

```sh
CONTAINER="$(cd .. && pwd)"
FABER_BIN="$CONTAINER/radix/target/debug/faber"
FABER_LIBRARY_HOME="$CONTAINER" "$FABER_BIN" check "$(pwd)"
FABER_LIBRARY_HOME="$CONTAINER" "$FABER_BIN" build "$(pwd)"
FABER_LIBRARY_HOME="$CONTAINER" "$FABER_BIN" test "$(pwd)"
```

Measured package-suite baseline (2026-10-03, isolated `inf1` packet):
`faber test <absolute-package-path>` took 157.74s with the plain development
CLI and 82.08s with a CLI built using `CARGO_PROFILE_DEV_OPT_LEVEL=1`.
These measure the MIR package suite, not model serving or GPU throughput.
In a packet, set `CONTAINER` to the packet root so its sibling libraries are used.

Model-serving stages must record the exact model path, size, hash, GGUF
metadata, command, request fixture, observed output, and comparison oracle.
Do not start long model or integration runs without making their expected cost
clear first.

## Measured baselines

A1 oracle path, `faber run --device metal inferentia -- live --backend metal`, eog case,
SmolLM2-360M-Instruct-f32 (1.45 GB), quiet M5 Max, release `faber`, 3 runs
(2026-10-08; radix `91e1b5947`, inferentia `2acf1cead`, gradus `27b282921`).
Full analysis and the ranked list: `../radix/docs/factory/gpu-reset/a1-perf-baseline.md`
(open defect F-33).

| Phase | min (s) | median (s) |
| --- | --- | --- |
| Front end (analyze 5.7 + MIR lowering/validation about 58) | 64.8 | 64.8 |
| Admit + digest + manifest + tokenizer | 35.3 | 35.5 |
| Tokenize + `port_resident` (second tokenizer build) | 4.7 | 4.7 |
| Load (third manifest parse + second digest + tensors 0.5) | 19.5 | 19.5 |
| Prefill, 9 tokens (includes first-use weight upload) | 5.1 | 5.2 |
| Wall | 129.6 | 130.0 |

Decode (64-token run, instrumented): 187 ms/token (5.35 tok/s), 676 launches/token;
about 44 percent is the interpreted logits scan, about 43 percent of the main thread
waits on Metal command-buffer completion triggered by buffer release. Peak RSS 7.4 GB.
Digest: 5.5 s per pass (software SHA-256, 261 MB/s) against 0.76 s with hardware SHA.
