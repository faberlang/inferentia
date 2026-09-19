# Inferentia

Inferentia is a local-first GGUF inference server written in Faber.

The repository currently contains the smallest viable Faber CLI shell and the
master development campaign. Model loading and HTTP serving begin in campaign
stage I1.

Source uses Faber's English reader locale through the canonical `[locale]`
manifest section introduced by the current Faber release line.

## Product boundary

Inferentia owns the user-facing inference product: configuration, CLI and API
contracts, request lifecycle, scheduling, streaming, cancellation, and
observability.

It consumes language and runtime capabilities from the Faberlang stack:

- Gradus owns model and machine-learning semantics.
- Faber owns application build and package composition.
- Radix owns compilation.
- Hosts own physical effects such as HTTP, files, clocks, and accelerators.

`llama.cpp` may be used as a reference oracle during development. It is not a
production dependency of Inferentia. Deployment is a separate work stream.

## Current commands

From this repository — the package imports `gradus:` and `norma:` providers,
so compilation needs the faberlang container as `FABER_LIBRARY_HOME`, the
workspace radix binary (the PATH `faber` lags main and fails package
resolution with `PKG001`), and an absolute input path:

```sh
CONTAINER="$(cd .. && pwd)"
FABER_BIN="$CONTAINER/radix/target/debug/faber"
FABER_LIBRARY_HOME="$CONTAINER" "$FABER_BIN" check "$(pwd)"
FABER_LIBRARY_HOME="$CONTAINER" "$FABER_BIN" build "$(pwd)"
```

In a `worktrees/<lane>/` packet the same form holds with the lane root as the
container; if the lane's `radix/target/debug/faber` is not built, override
`FABER_BIN` to a built workspace binary.

The CLI has no serving command yet. See the
[Inferentia master campaign](docs/factory/inferentia/CAMPAIGN.md) for the staged
delivery plan and completion gates.
