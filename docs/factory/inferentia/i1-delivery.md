# I1 Delivery Specification — Small GGUF vertical slice (P3)

**Campaign**: Inferentia master campaign (I1 — Small GGUF vertical slice)
**Author**: planner-1 (task `196fb361`)
**Date**: 2026-08-09
**Companion evidence**: [`i1-discovery.md`](i1-discovery.md) — every fact below
traces to live verification recorded there.
**Baseline**: inferentia repo clean at `ed845e6`; gradus HEAD `24feb82`;
faber-runtime HEAD `3e2f8d9`; faber 1.5.0; llama.cpp 10150 `dee2a846b`
(oracle only).

---

## 1. Interpreted Unit

Serve the local SmolLM2-360M-Instruct-Q4_K_M GGUF end to end through a
Faber-written local server: one documented start command, load-once weights,
a health endpoint with explicit states, a model identity endpoint, and a
non-streaming generation endpoint that returns multiple tokens for a frozen
request and matches the frozen oracle. Then add the two Qwen2.5 Q4_K_M rows as
one batch (same architecture/tokenizer/quantization/execution path — proven in
discovery §2.4) or split at the documented boundary.

Discovery answers the campaign's open decisions and entry-evidence
requirements; this spec locks the contracts, the unit graph, and the blocking
prerequisite deliveries.

## 2. Normalized Spec

**Scope (in)**: product contracts for serve CLI, HTTP API, configuration
precedence, generation parameters, admission, shutdown; the frozen fixture +
oracle comparison; validation-log capture per the cross-stage validation
record (campaign §206–217).

**Scope (out)**: streaming (I2), chat templating, concurrency beyond one
request at a time, dynamic model admission via API, deployment/provisioning,
performance qualification, accelerator backends, HTTP client, `llama.cpp` as
anything but a comparison oracle.

**Ownership routing** (campaign §49–54): Gradus semantics consumed, never
reimplemented in Inferentia; physical effects via Host providers; reusable
gaps become blocking deliveries in their owning repos; deployment stays out.

## 3. Repo-Aware Baseline

- **inferentia**: I0 shell only — `faber.toml` (rust/bin, no deps, no host
  bootstrap), `src/main.fab` (empty `main`), README + campaign + AGENTS.
  No `scripta`; validation = `faber check .` / `faber build .` (AGENTS.md).
- **gradus**: full GGUF admission (SmolLM2 row), capsule, dequant, tokenizer
  identity, decode/cache/sampling/generation contracts — compile-validated,
  runtime env-blocked.
- **faber-runtime**: pinned-row admission (`model_format`), tensor view
  (`model_widen`), 32-layer CPU decoder (`cpu_oracle`), greedy record
  (256 tokens, all_agree), GI2 goldens — Rust-tested. No tokenizer runtime
  (removed PML2 C3), no execution bridge to Faber apps.
- **hosts**: `http` (loopback, single request, no streaming), `solum` (file
  read/size), `tempus` (clock) providers implemented; auto-selected by route
  prefix when `[target.rust] host = "native"` is set.
- **norma**: `http` server wrappers live; `json` and `toml` codecs deferred.
- **radix factory GI4** (`radix/docs/factory/gpu-inference-gguf/`): frozen
  session contract types (`ModelInstance`, `ExecutionSession`,
  `SequenceState`, `Invocation`) — consumed as vocabulary, not as code.

## 4. Contract Decisions (locked)

### D1 — `serve` CLI syntax

```
inferentia serve [--model <PATH>] [--port <PORT>] [--host <HOST>]
                 [--max-tokens <N>] [--context <N>] [--seed <N>]
                 [--log-level <info|warn|error>] [--help] [--version]
```

- `--model` (alias `-m`): required. Absolute or relative path to the GGUF.
- `--host`: default `127.0.0.1` (loopback — the http provider binds loopback
  only). `--port`: default `8080`; `0` = ephemeral (used by tests).
- `--max-tokens`: server-level default output ceiling; default `32`.
- `--context`: session context ceiling; default = the model's
  `context_length` (8192 for SmolLM2).
- `--seed`: deterministic seed (Semen rule: ≥ 1); default `1`.
- `--log-level`: stderr verbosity; default `info`.
- `serve` is the only subcommand in I1. Unknown flags / missing `--model` /
  invalid port are usage errors → exit code 1 before any listen.

### D2 — Configuration precedence

Order (fixed as a contract): **model-derived facts < documented constants <
server flags < request body**. No config file in I1 (`norma:toml` deferred);
the precedence position for a future file layer is reserved between
documented constants and server flags. Request-body fields override server
flags per request; absent body fields inherit server flags; absent flags
inherit defaults. `max_tokens`/`context`/`seed` from flags are ceilings/
defaults, never per-request overrides of explicitly-supplied values.

### D3 — Minimum HTTP endpoints and schemas

All responses JSON; loopback HTTP/1.1; one request at a time.

| Endpoint | Method | Semantics |
| --- | --- | --- |
| `/health` | GET | Always 200 once the listener is up. Body `{"state":"starting"\|"ready"\|"failed","model":null\|{…},"pid":N}`. `starting` while admitting; `ready` after admission; `failed` on admission failure (with typed error text in `model.error`). |
| `/model` | GET | Admitted model identity + limits (when ready). `{"name":…,"architecture":"llama","quantization":"q4_k_m","file_size_bytes":270590880,"sha256":"2fa3f013…","context_length":8192,"vocab_size":49152,"max_output_tokens":<server default>,"backend":"cpu"}`. 503 with `{"state":"starting"\|"failed"}` before ready / on failure. |
| `/generate` | POST | Request JSON `{"prompt":<textus>,"max_tokens":N,"temperature":F,"top_k":N,"top_p":F,"min_p":F,"repeat_penalty":F,"seed":N}`. Response JSON `{"model":…,"text":<textus>,"tokens":[<ids>],"finish_reason":"length"\|"eos"\|"stop","usage":{"prompt_tokens":N,"completion_tokens":N,"total_tokens":N}}`. |

- Field names map 1:1 to the gradus `GeneratioConfigura` authority
  (`contextus`, `magna_promptus`, `maxima_verborum`, `semen`, `temperatura`,
  `top_k`, `top_p`, `min_p`, `poena_repetitionis`); unknown or out-of-domain
  fields are rejected (`imperium_admissum` reject rows — fail closed, never
  silently ignored).
- `prompt` is the only text in I1; generated `text` is the raw detokenized
  output (no chat template — the metadata chat templates are recorded, not
  applied).
- Response codes: 200 ok · 400 malformed JSON / unknown field / rejected
  parameter / empty prompt · 413 body too large (provider cap) · 404 unknown
  path · 503 starting or failed · 500 internal. Default body cap 1 MiB.
- `finish_reason`: `"length"` at `max_tokens`; `"eos"` when an EOG id {0,2} is
  produced; `"stop"` on server shutdown mid-generation (cancelled).
- **JSON codec decision**: `norma:json` is deferred; I1 owns a **minimal,
  bounded JSON assembler/parser in Inferentia product code** covering exactly
  the three schemas above (tested against the frozen fixture). It is not a
  reusable primitive — the second-caller rule triggers a Norma `json` codec
  delivery (I2 prerequisite), recorded in §9. TOML config is excluded for the
  same reason (D2).

### D4 — Initial generation parameters + deterministic defaults

- Default profile is **deterministic greedy**: `temperature 0.0`, `top_k 0`,
  `top_p 1.0`, `min_p 0.0`, `repeat_penalty 1.0`, `seed 1` (Semen ≥ 1).
  Unadorned requests are reproducible. Stochastic sampling requires an
  explicit `temperature > 0` in the request.
- Limits enforced server-side before decode: `1 ≤ max_tokens ≤ context`;
  prompt length must fit `context`; `max_tokens` default 32, context default
  = model limit. Reject, never truncate (gradus cursor contract).
- EOG stop set = `{0, 2}` (pinned). Generation terminates after the first EOG
  token; `max_tokens` is a ceiling, not a promise.
- **Batching/split decision**: Slice 1 = SmolLM2 single row. Slice 2 = the two
  Qwen rows as **one batch** (same arch/tokenizer/quant/execution path —
  discovery §2.4). The batch is split only if a real boundary surfaces at
  execution time (recorded with evidence).

### D5 — Model admission errors and process exit

- Admission is **startup-only**: bind listener → admit → ready. `admit`
  (digest verification first, then structure validation) runs **before any
  weight materialization** — unsupported/malformed artifacts fail before
  model allocation (gate).
- Admission failure → `/health` serves `{"state":"failed"}` with the typed
  cause (GgufError variant text: FormatMala / VersioIgnota / ArchitecturaMala
  / QuantizatioIgnota / OffsetMala / FormaMala / TokenizerMala / LimitesMala
  / WireMala / CapsulaMala); the process stays up to be observable and exits
  on shutdown.
- **Exit codes**: `0` clean shutdown (SIGTERM/SIGINT after drain) · `1` usage/
  config error · `2` admission/load failure at shutdown · `130` forced second
  signal. Startup usage errors exit immediately with 1.

### D6 — Shutdown and in-flight behavior

- SIGTERM/SIGINT → stop accepting (`http:stop` closes the listener and
  pending streams) → wait for the in-flight request (one at a time in I1) to
  finish or cancel at the next gradus cancellation checkpoint
  (`observa_cancellationem` per decode step) → exit 0.
- A second signal forces immediate exit (130).
- "Leaves no listener behind" is proven by a test that rebinds the same port
  after shutdown.

## 5. Blocking prerequisite deliveries (rejoin I1 after narrow proofs)

These are campaign scope-routing products: gaps in owning repos, **not**
Inferentia compatibility code. Each has a narrow proof; I1's runtime units are
blocked until the relevant proofs pass.

### BD-1 — Gradus tokenizer runtime encoder (BBPE text→ids)

- **Why**: no executable encoder exists (removed from faber-runtime at PML2
  C3; gradus `tokenizer.fab` pins expected ids only). Every generation
  request starts from text.
- **What**: a runtime `encode(textus) → lista<numerus>` for the admitted
  tokenizer row(s) (gpt2/smollm for slice 1; gpt2/qwen2 for the batch) in
  Gradus, using the row's tokens/merges/token_type arrays, honoring
  BOS-free/space-prefix-free and special-token parsing.
- **Narrow proof**: `faber test` on gradus proba encoding probes P1–P11 and
  the four workload prompts → exact pinned id lists (embedded fixtures);
  differential vs `llama-tokenize` 10150 (24-case set from
  `evidence/contract-tokenize-probes.txt`) matches on every case.
- **Dependency**: requires the library-execution vehicle (BD-3) or its own
  execution path. If BD-3 cannot land first, this delivery states its partial
  status honestly and I1's tokenization gate stays blocked.

### BD-2 — Execution bridge: Faber app → pinned-row engine

- **Why**: the engine (admission + forward + greedy) is Rust in faber-runtime;
  compiled Faber code cannot call it today.
- **What (recommended)**: expose the engine to Faber applications via
  **faber-runtime library-provider bindings** (`[library] provider` +
  `bindings/rust.toml`, sqlite precedent) — routes `model:admit(path)`,
  `model:forward(tokens)`, `model:tokenize(text)` (once BD-1 exists),
  `model:generate(config, prompt)` shaped by the Gradus contract vocabulary
  (GeneratioConfigura nine fields, EOG {0,2}, reject-not-truncate). Fallback:
  a `model:*` host provider in `hosts` — choose only if bindings prove
  heavier (per-call valor marshaling for 49,152-logit vectors is the
  differentiator).
- **Narrow proof**: a compiled Faber probe calls `model:admit` on the SmolLM2
  file → returns SHA-256 `2fa3f013…`; `model:forward` on the pinned 9 tokens →
  logits digest equals the GI2 golden (`gi2-3-logits-golden/logits-pos0.json`);
  three greedy tokens equal `record.json` prefix. Validation in the owning
  repo: `cargo check -p faber-runtime` + `cargo nextest run -p faber-runtime`
  (or the provider's crate); the Faber probe via `faber check .` + `faber
  build .`.

### BD-3 — Library-proba execution vehicle (FMIR stepper / library-import gap)

- **Why**: every gradus module records runtime value-identity as env-blocked
  ("FMIR stepper / library-import gap"). Gradus proba and any Gradus runtime
  code cannot execute yet.
- **What**: Radix/Faber close the library-execution gap so `faber test` runs
  library proba (not just compile-level checks).
- **Narrow proof**: `faber test` executes a gradus proba (e.g., `sampling`
  greedy `maxima` pin and `generation` config round-trip) and returns a value.
- **Note**: this may itself be a substantial Radix/Faber delivery; if it
  cannot land, I1 proceeds on BD-2 (Rust engine) and the Gradus-semantic layer
  is consumed as contract, with the value-identity gate honestly deferred.

### BD-4 — Qwen2 row-contract extension (batch prerequisite)

- **Why**: the admission contract and engine are pinned to the SmolLM2 row;
  the Qwen rows are rejected by today's contract (arch `qwen2`, vocab 151,936,
  untied output head, per-row parameters — discovery §2.2/2.3).
- **What**: gradus `model/gguf.fab` gains a second admitted row contract (the
  two qwen2 rows: shared arch/tokenizer/quant/execution path); faber-runtime
  `model_format` + engine gain qwen2 admission and parameterization (untied
  output head, per-row layer/head/embedding constants). Tokenizer pre `qwen2`
  encoder rides BD-1.
- **Narrow proof**: both qwen2 files admit with correct digest and capsule
  identity; a forward produces finite full-vocab logits; greedy tokens match
  the fresh llama.cpp oracle run for both rows (recorded in the batch
  validation log).
- **Dependency**: joins after Slice 1 passes (campaign batching rule).

### BD-5 (optional, deferred to I2) — Norma `json` codec

Not required for I1 (product-owned minimal JSON covers the three fixed
schemas). Triggered by a second caller; becomes a required prerequisite in I2.

## 6. Stage Graph (implementation units)

### Slice 1 — SmolLM2 single row end-to-end

| Unit | Done-when (exact) | Validation (narrowest proof) |
| --- | --- | --- |
| **U1** serve CLI + host bootstrap | `inferentia serve --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --port 8080` binds a listener; `--help`/usage errors exit 1; `faber.toml` sets `[target.rust] host = "native"`; CLI precedence per D1/D2 | `faber check .` green; `faber build .`; binary start + `curl -s localhost:8080/health` |
| **U2** Admission at startup + health lifecycle | Listener binds first; `admit` runs before allocation; `/health` shows `starting` then `ready` with model identity; admission failure (missing file, truncated copy, digest-mismatch fixture) → `failed` state + exit 2 on shutdown; no weight materialization on failure | Unit tests over the admission path; manual curl against live server; failure fixtures from local copies (truncate/corrupt in a test tmpdir) |
| **U3** `/model` endpoint | Response schema per D3 from capsule + admission facts (name, arch, quant, size, sha256, context, vocab, max_output_tokens, backend `cpu`) | curl `/model` → exact JSON vs committed expected body; 503 before ready |
| **U4** `/generate` endpoint | Request parse (minimal product JSON), field validation via gradus reject-rows, generation loop: encode → prefill → decode/greedy loop with EOG stop {0,2}, `max_tokens` budget, cancellation checkpoints; second sequential request succeeds **without reloading weights** (resident-model proof) | curl frozen fixture request → ≥ 16 tokens; two sequential requests; stderr shows one load |
| **U5** Oracle match (tokenization + greedy) | P10 encodes to `[504,…,2767]`; generated token ids equal `record.json generated_tokens[0..16]` **exactly** (documented tolerance: exact, GI2 §4.1 top-1 non-EOG surface) | Compare against `record.json` + fresh `llama-cli`/`llama-tokenize` run recorded in validation log |
| **U6** Shutdown + in-flight | SIGTERM during idle → exit 0; SIGTERM mid-request → in-flight request finishes or cancels at the checkpoint; listener closed (same port rebinds); second signal → exit 130 | Shell test sequence with `kill -TERM`, port rebind check, curl loop |
| **U7** Admission-failure matrix | Malformed GGUF, wrong arch, wrong quant, digest mismatch, unknown key → typed failure before allocation, no listener behavior regression | Fixture matrix (local copies) driving each GgufError variant |
| **U8** Validation-log capture | Cross-stage record complete: repo commits (inferentia, gradus, faber-runtime, hosts, faber), exact commands, model path/size/hash, request fixture + bodies, stdout/stderr, HTTP statuses, process-lifetime + shutdown evidence, oracle command + plain match statement | `docs/factory/inferentia/i1-validation.md` committed with Slice-1 gate run |

### Slice 2 — Qwen batch (joins after Slice 1 passes)

| Unit | Done-when | Validation |
| --- | --- | --- |
| **U9** Qwen batch wiring | Both Qwen rows serve through the same U1–U7 path with per-row facts (arch `qwen2`, vocab 151,936, context 32,768, untied head); admission accepts both; generation matches a fresh oracle trace for each | Same gate commands per row; batch boundary re-confirmed or split recorded with evidence |

## 7. Completion-Gate Mapping (campaign §119–130 → units)

| Campaign gate | Proven by |
| --- | --- |
| A named model starts with one documented command and loads once | U1 + U2 (load-once, stderr evidence) |
| Health endpoint distinguishes starting/ready/failed | U2 |
| Model endpoint reports admitted identity and limits | U3 |
| Generation endpoint returns multiple tokens for a frozen request | U4 (frozen fixture §6 of discovery) |
| Two sequential requests without reload | U4 |
| Unsupported/malformed artifacts fail before allocation | U2 + U7 |
| Tokenization + deterministic selection match oracle within documented tolerance | U5 (exact, GI2 §4.1) |
| Shutdown releases resources, no listener behind | U6 |
| Production binary does not invoke/link llama.cpp | U1 (binary linkage evidence; llama.cpp used only in U5/U8 oracle runs) |
| Same proof for all three rows or recorded boundary | U9 (batch) or boundary record |

## 8. Implementation Work

- **Parallelism**: BD-2, BD-3, and BD-1 (after BD-3) are independent of each
  other; U1/U3 are independent of the engine; U2/U4–U7 depend on BD-1 + BD-2.
  Safe parallel tracks: (a) BD-2/BD-3 (radix/faber-runtime), (b) BD-1 +
  gradus, (c) inferentia U1/U3/U6/U7 product contracts (stub-free, tested
  against the contract shapes). Write surfaces are disjoint.
- **Ownership**: blocking deliveries land in their owning repos with their
  own protocols (cargo discipline applies — narrow `cargo check -p <crate>` /
  single-crate tests in-loop; closeout via the ladder the owning repo
  declares).

## 9. Checkpoints and Gates

- **Gate A (Slice 1)**: all BD-1/BD-2/BD-3 proofs pass + U1–U8 done-when met;
  one run of the Slice-1 validation (`faber check .` + `faber build .` +
  the §7 gate commands) recorded in `i1-validation.md`.
- **Gate B (Slice 2)**: BD-4 proof passes + U9 done-when for both Qwen rows;
  or the campaign records the exact boundary that split the batch.
- **Batching/split decision**: one batch for the Qwen pair (evidence §2.4);
  split only on a real boundary discovered at execution time.
- **Release posture**: `defer-release` — no faber product release is touched
  by I1 (inferentia is a sibling app repo, no release protocol).
- **Stop conditions**: campaign §231–235 apply. BD-3 (library execution) is
  the largest unknown; if it does not land, the Gradus value-identity gate is
  deferred (BD-2 keeps I1 end-to-end on the Rust engine) and the boundary is
  reported, not hidden.

## 10. Validation

- Inferentia-owned units: `faber check .` + `faber build .` (narrow, no cargo
  workspace); run the binary, curl the loopback endpoints.
- Owning-repo blocking deliveries: `cargo check -p <crate>` + single-crate
  `cargo nextest run` (faber-runtime/hosts), `faber test` (gradus proba, no
  cargo), per BD proofs.
- Oracle runs are recorded, never authoritative: `llama-tokenize` /
  `llama-cli` 10150 `dee2a846b` with fixed flags in the validation log.
- Expected model-side cost (AGENTS.md): Slice-1 full gate run is a small
  model (270 MB, CPU) — minutes, not hours. The GI2 greedy reference (~64 s
  release) bounds the comparable oracle run.

## 11. Open Questions

1. BD-2 vehicle: library-provider bindings (recommended) vs `model:*` host
   provider — operator decision; the fallback is documented.
2. BD-3 (library execution gap) is a large Radix/Faber delivery — confirm it
   is budgeted as a campaign prerequisite, or accept the deferred
   value-identity gate with the Rust engine as the I1 runtime.
3. Product-owned minimal JSON for I1 is accepted as a bounded exception to
   "no Inferentia-specific compatibility code" — confirm, with the Norma codec
   as the committed I2 replacement.

## 12. Companion Skill Plan

- `delivery` — this spec (planning only).
- `factory` — executes units once the blocking proofs pass.
- `auditor` — owns stages 4–6 / full-profile runs at named boundaries.
- `polish` — per-unit single-pass closeout over touched primary sources.
