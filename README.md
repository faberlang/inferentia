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

From this repository:

```sh
faber check .
faber build .
```

The CLI has no serving command yet. See the
[Inferentia master campaign](docs/factory/inferentia/CAMPAIGN.md) for the staged
delivery plan and completion gates.
