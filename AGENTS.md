# Inferentia Agent Guide

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

Run the narrowest useful proof first:

```sh
faber check .
faber build .
```

Model-serving stages must record the exact model path, size, hash, GGUF
metadata, command, request fixture, observed output, and comparison oracle.
Do not start long model or integration runs without making their expected cost
clear first.
