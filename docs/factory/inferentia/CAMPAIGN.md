# Inferentia Master Campaign

**Status**: active — I1 delivery admitted (auditor-4 d9fb5375); U1/U2/U3/U4/U5/U7 + D5-exit fix landed; remaining Slice-1 = U6/U8; provider ruling 2615e6a9 (A): gradus owns admit/tokenize/generate as `gradus:*` — I-1/I-2 remapped inferentia off deleted `faber-runtime/model`; BD-1 now G3 `tokenize` (tables not yet loaded from the admitted row — frozen-fixture fallback remains); BD-3 deferred; BD-4 open

## Summary

Build Inferentia as a Faber-written, local-first GGUF inference server. Deliver
one small model end to end first, establish a production floor with a local
Qwen 35B model second, and treat DeepSeek V4 Flash as a gated stretch goal.

This is a routing campaign. Each implementation stage must first be lowered
into a delivery specification with exact contracts, dependencies, fixtures,
commands, owners, and completion oracles. Factory sessions execute those
specifications. Campaign prose alone never counts as completion.

## Problem

The Faberlang stack has compiler, runtime, host, and ML pieces, but it does not
yet have a Faber application that owns the complete inference-server product.
The missing product surface includes model admission, lifecycle, generation
requests, scheduling, cancellation, streaming, observability, and stable CLI
and HTTP contracts.

## Desired end state

Inferentia can load a supported GGUF once, keep it resident, and serve repeated
generation requests through explicit local interfaces. Unsupported artifacts
fail before expensive allocation. The production path is implemented through
Faberlang components and does not shell out to or link against `llama.cpp`.

## Development posture

- Make a clean product boundary. Inferentia remains a sibling application repo.
- Implement the first vertical slice before designing broad abstractions.
- Use exact model rows, not claims of generic GGUF support.
- Use `llama.cpp` only for controlled token and output comparisons.
- Split reusable ML, compiler, build, or host prerequisites into their owning
  repositories with explicit dependency gates.
- Keep deployment, service installation, and machine provisioning outside this
  campaign.
- Do not copy or download model artifacts merely to advance planning.

## Scope routing

| Concern | Owner | Inferentia responsibility |
| --- | --- | --- |
| CLI, API, configuration, lifecycle | Inferentia | Define and implement product contracts |
| Admission, scheduling, cancellation, streaming | Inferentia | Own request policy and behavior |
| Model, tensor, tokenizer, decode semantics | Gradus | Consume stable library contracts; file precise gaps |
| Parsing, lowering, code generation | Radix | Depend on verified compiler behavior |
| Build and package composition | Faber | Consume user-facing build commands |
| HTTP, file, clock, accelerator effects | Hosts | Consume provider contracts and identify missing effects |
| Reference output | `llama.cpp` | Comparison oracle only |
| Installation and deployment | Separate campaign | Out of scope here |

## Campaign path

```text
I0 Repository foundation
  -> I1 Small GGUF vertical slice
      -> I2 Qwen 35B production floor
          -> I3 DeepSeek V4 Flash stretch
```

I1 may expose reusable prerequisites in Gradus, Radix, Faber, or Hosts. Those
become explicit blocking deliveries and rejoin I1 only after their own narrow
proofs pass. I2 and I3 do not bypass an incomplete earlier stage.

## I0 — Repository foundation

**State**: scaffolded in the working tree; uncommitted; 1.5 validation pending

The repository has a minimal Faber binary manifest, a compilable CLI entry
point, local agent guidance, a README, and this campaign. It intentionally has
no fake `serve` command or parked server implementation.

Completion gate:

- The repository is independently initialized on `main`.
- `faber check .` passes with Faber 1.5.0 or newer.
- The ownership boundary is recorded in `README.md` and `AGENTS.md`.
- I1 has enough evidence to be lowered into a delivery specification.

## I1 — Small GGUF vertical slice

**State**: Slice-1 product units U1–U5/U7 landed on `main` (U3/U7 2026-08-11).
Provider ruling 2615e6a9 (2026-08-18): gradus is the model provider — public
`gradus:*` routes over its admission contract + decode + G2 generate + G3
tokenize. Inferentia locks and imports remapped off deleted
`../faber-runtime/model` (I-1/I-2). Remaining Slice-1 = U6/U8. BD-1 is now
G3 `tokenizator.tokenize` (vocab/merge tables not yet loaded from the
admitted row — frozen-fixture fallback remains). BD-3 deferred. BD-4 open
(Slice 2 blocked). BD-2's faber-runtime `model:*` vehicle is superseded.

### Goal

Serve the local `SmolLM2-360M-Instruct-Q4_K_M.gguf` end to end. Once that row
passes, add the two local Qwen rows as one batch only if they use the same
architecture, tokenizer, quantization, and execution path:

- `Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`
- `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`

Split either Qwen model into a separate delivery if it crosses a real support
boundary.

### Required contract decisions

- Exact `serve` CLI syntax and configuration precedence.
- Minimum HTTP endpoints and request/response schemas.
- Initial generation parameters and deterministic defaults.
- Whether I1 is deliberately non-streaming or includes a minimal stream.
- Model admission errors and process exit behavior.
- Shutdown and in-flight request behavior.

### Entry evidence

- Record each artifact's absolute path, byte size, SHA-256, GGUF version,
  architecture, tensor types, quantization, tokenizer metadata, and context
  limits.
- Identify the exact Gradus APIs available for GGUF loading, tokenization,
  forward execution, cache management, sampling, and generation.
- Identify the exact Norma/Host HTTP behavior available to a Faber application.
- Freeze a small prompt fixture and a `llama.cpp` comparison command.

### Completion gate

- A named model starts with one documented command and loads once.
- A health endpoint distinguishes starting, ready, and failed states.
- A model endpoint reports the admitted model identity and supported limits.
- A generation endpoint returns multiple tokens for a frozen request fixture.
- Two sequential requests succeed without reloading weights.
- Unsupported or malformed artifacts fail before model allocation.
- Tokenization and deterministic token selection match the frozen oracle within
  an explicitly documented tolerance.
- Shutdown releases resources and leaves no listener behind.
- The production binary does not invoke or link against `llama.cpp`.
- The same proof passes for all three small rows, or the campaign records the
  exact boundary that split the batch.

## I2 — Qwen 35B production floor

**State**: planned; blocked on I1 and its reusable engine prerequisites

### Goal

Serve one local Qwen 35B GGUF as the minimum production requirement. The
default qualification artifact is:

`/Users/ianzepp/ai/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`

The delivery specification may select another local Qwen 35B row only after it
records why that artifact is the better production qualification target.

### Additional production gates

- Admission computes a memory budget before allocating weights or KV cache.
- Weights remain resident across warmed sequential requests.
- Context and output ceilings are enforced and reported through the API.
- Streaming, client disconnect, explicit cancellation, and clean shutdown have
  behavioral tests.
- Concurrency policy is explicit, bounded, and observable.
- Logs or metrics expose load, prefill, decode, token, queue, cancellation, and
  error phases without leaking prompt content by default.
- A repeatable qualification run records startup time, first-token latency,
  decode rate, peak memory, backend, and exact model hash.
- The server survives repeated requests without unbounded memory growth.
- A controlled `llama.cpp` run supplies comparison evidence, not implementation.

### Stop conditions

Stop and split owning-repository work when the failure is a missing reusable ML
primitive, compiler feature, packaging feature, or physical Host effect. Do not
hide those gaps behind Inferentia-specific compatibility code.

## I3 — DeepSeek V4 Flash stretch

**State**: stretch; blocked on I2 and exact artifact discovery

### Goal

Determine whether the archived DeepSeek V4 Flash GGUF can be admitted and
served on this machine. A custom implementation across the controlled stack is
allowed when the model cannot run through the existing path.

### Entry gate

Before transferring the artifact from the Pharos archive, record:

- Archive path, byte size, SHA-256, GGUF version, architecture, quantization,
  tokenizer metadata, tensor inventory, and declared context.
- Expected resident-weight and KV-cache budgets for this machine.
- Whether current `llama.cpp` recognizes and can execute the exact artifact.
- Which gaps belong to Inferentia, Gradus, Radix, Faber, or Hosts.
- The transfer command, destination, free-space check, and cleanup plan.

Artifact transfer requires a separate, explicit execution decision. The model
is not currently assumed to be present on this machine.

### Completion gate

- The artifact is either served through a documented bounded configuration, or
  the campaign ends with a source-grounded infeasibility result.
- Any custom support is placed in the owning layer and has a model-independent
  contract where reuse is real.
- Admission and memory-budget checks prevent unsafe overcommit before loading.
- The qualification report records exact artifact identity, backend, memory,
  latency, throughput, context, output, and comparison evidence.
- No claim of DeepSeek support is made from metadata parsing or model loading
  alone; generation must produce verified multi-token output.

## Cross-stage validation record

Every model qualification must preserve:

- repository commit identifiers for every participating Faberlang component;
- exact build and run commands;
- model path, size, and SHA-256;
- request fixtures and expected result shape;
- observed stdout, stderr, HTTP status, and response body;
- process lifetime and shutdown evidence;
- backend and device identity;
- memory and timing observations appropriate to the stage;
- oracle command and a plain statement of what did and did not match.

## Open decisions

- The stable HTTP compatibility target, if any.
- The I1 streaming cut line.
- CPU-only versus accelerator-backed first execution.
- The concurrency model after the single-request proof.
- The exact Qwen 35B qualification row if the default artifact is unsuitable.
- Whether DeepSeek V4 Flash is recognized by current tooling and fits after
  quantization.

These decisions belong in the delivery specification for the first stage that
needs them. They should not be guessed into the scaffold.

## Campaign stop conditions

The campaign is complete when I1 and I2 pass their gates and I3 has either
passed or produced a documented, evidence-backed infeasibility decision. Stop
earlier and report the boundary when machine capacity or a fundamental model
constraint makes the desired stage impossible. Deployment remains separate
even after the product campaign completes.
