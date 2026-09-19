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
```

Model-serving stages must record the exact model path, size, hash, GGUF
metadata, command, request fixture, observed output, and comparison oracle.
Do not start long model or integration runs without making their expected cost
clear first.
