# GOAL: prefix-reuse-consumer — tenant-scoped prepared-state retention and warm request evidence

**Status**: deferred — shelved at the 2026-09-20 registry reboot; pre-implementation; recoverable
**Created**: 2026-08-21
**Campaign:** `speculative-decode`
**Source:** operator expansion of the SD5 consumer/evidence boundary, grounded in the live Inferentia server, generate gate, and Gradus prepared-state contract
**Repos:** primary: `inferentia/`; dependency evidence: `gradus/`, Hosts clock/streaming contracts
**Related:** [`../../../../gradus/docs/factory/prepared-prefix-state/goal.md`](../../../../gradus/docs/factory/prepared-prefix-state/goal.md); [`Inferentia I2`](../inferentia/CAMPAIGN.md#i2--qwen-35b-production-floor) (planned, blocked on I1; owns the streaming production gate); [`I1 host-effect discovery`](../inferentia/i1-discovery.md#51-http-server-effect--available-but-bounded) (names the missing streaming effect); `norma:tempus` / Hosts clock is live

---

## Invariant

Inferentia reuses a prepared prefix only from an explicitly authorized,
private tenant/session scope after exact identity and payload verification.
The longest valid candidate may skip prefix prefill, but a cold and warm run
with the same request configuration emits identical token IDs and text. Each
run records honest cold/warm first-token timing without exposing raw token keys
or claiming a speedup that was not measured.

This is a single-node product lifecycle. Multi-device tiers, placement, and
routing belong to MD4D, not this goal.

## Problem

Inferentia currently keeps model weights resident but creates fresh KV caches
for every generation: `src/main.fab:965-1007` defines `ResidentModel` and
`fresh_resident_caches`, while `src/main.fab:1448-1462` calls the fresh-cache
path on each request and discards generated state. The existing
`tests/generate-gate/src/main.fab:473-497,620-649` proves two deterministic
requests without reloading weights; it does not prove KV or prefix reuse.

The request schema has prompt and sampling fields only
(`src/main.fab:160-181`). The server accepts one request at a time with no
session/cache registry or candidate index (`src/main.fab:1840-1936`). There is
therefore no tenant scope, retention lifecycle, exact candidate verification,
capacity bound, eviction policy, or request-to-prefix matching surface.

The current serving tokenizer path does not support arbitrary prompts:
`src/main.fab:727-740` builds empty tokenizer tables and falls back to the one
frozen prompt in `src/main.fab:126-135,720-725`. The product cannot prove reuse
against a long document until the real Gradus tokenizer/decoder path is wired
and the context limit is enforced from admitted model facts.

The current SSE route sends generated tokens only after the batch generation
has completed (`src/main.fab:874-887`), and the server imports no clock or
metrics provider (`src/main.fab:46-63`). It cannot currently measure true
first-token latency. A warm TTFT receipt therefore depends on an actual
first-token streaming boundary and a Hosts clock contract.

## Proposal

Implement a product-owned, single-node prepared-state consumer around the
Gradus prepared-state contract.

### Scope and lifecycle

Inferentia owns the request/session policy and a bounded retention index. Each
entry is private to a tenant/session scope and contains an opaque product
handle, Gradus canonical identity, payload binding, byte/accounting facts,
last-use state, and lifecycle status. Public requests and logs expose the
opaque handle and timing/status fields, never raw token IDs, raw token-prefix
keys, or prompt content by default.

The lifecycle is explicit:

1. tokenize and canonicalize the prompt through the admitted Gradus path;
2. enumerate only candidates authorized for the requesting tenant/session;
3. ask Gradus to verify identity/payload and select the longest exact prefix;
4. continue from that state or create a fresh cache when no candidate applies;
5. publish the resulting prepared state under the same private scope only after
   successful verification and generation;
6. release, expire, or evict entries under the bounded policy.

Inferentia never reconstructs or weakens Gradus identity rules. A candidate
with a model, configuration, tokenizer, position, state-family, or payload
mismatch is not attached. The default no-match behavior is a cold run; a
malformed candidate is recorded as a rejected candidate, not silently used.

### Capacity and eviction

The index has an explicit byte and entry budget. The default policy is
deterministic least-recently-used eviction within a tenant scope, with active
continuations protected until release. Accounting includes KV and any
recurrent/SSM/convolution payload required by the model. Allocation, overflow,
eviction, and release are observable without logging prompt content. There is
no unbounded process-global map.

### Timing and equality evidence

The request lifecycle records host-clock timestamps for admission, tokenize,
candidate verification, prefix selection, remaining prefill, first token,
and completion. The response stream must expose the first-token boundary
before the full generation completes. Cold and warm runs use the same model
identity, prompt, full generation configuration, seed, and output ceiling.

The closeout receipt contains:

- cold and warm selected-prefix lengths and verification outcomes;
- exact token IDs and detokenized text, with equality asserted;
- cold and warm TTFT plus the timestamp source and backend;
- proof that the warm route skipped the reused prefix prefill;
- capacity, eviction, tenant/session scope, and process commit identifiers.

No fixed speedup threshold is assumed. If warm TTFT does not improve on a
given backend, the receipt states that result instead of converting reuse into
a performance claim.

### Non-goals

- No implementation of Gradus cache/state identity, payload verification, or
  model/tokenizer semantics. Those belong to
  `gradus/docs/factory/prepared-prefix-state/goal.md`.
- No raw token-key API, cross-tenant sharing, implicit authorization, or
  prompt-content logging.
- No multi-device placement, tiers, migration, or routing. MD4D owns that
  boundary; this goal remains one-node and one-product-process.
- No CUDA/Metal kernel, allocator, quantized-KV, or device-residency work.
- No continuous batching, broad scheduler redesign, model-drafter weights, or
  speculative verification policy.
- No deployment, service installation, or fixed throughput/TTFT promise.

## Units (lowering sketch — refine via `$delivery`)

All units below are admitted and mandatory. There are no optional or deferred
units in this goal.

| Unit | Scope | Depends on | Hand evidence |
| --- | --- | --- | --- |
| 1 | Product request/session contract: opaque prepared handle, tenant/session scope, attach/continue/release lifecycle, and response/status fields. Update `src/main.fab` and the Inferentia API/factory docs without exposing raw token keys. | Gradus prepared-state identity contract; existing Inferentia request policy | `faber check .`; schema/reject fixtures; no raw-key scan of responses/logs |
| 2 | Private retention index with exact scope, byte/entry accounting, deterministic eviction, active-continuation protection, expiry, release, and fail-closed overflow behavior. | 1; Gradus payload binding; single-node process lifecycle | Unit/integration cases for isolation, capacity, eviction, release, and restart |
| 3 | Exact candidate verification and longest-prefix consumer path. Inferentia supplies only authorized candidates to Gradus, records cold fallback versus rejected candidate, and publishes a new prepared state only after verified continuation. | 1, 2; Gradus attach/continue implementation | Candidate matrix for model/config/tokenizer/position/payload/tenant mismatches; longest-prefix receipt |
| 4 | Arbitrary prompt/tokenizer and detokenizer integration through the admitted Gradus route, including long-document context validation. Remove the frozen-prompt-only serving dependency; preserve fail-closed limits. | Gradus tokenizer runtime and model context facts; 1 | Exact tokenization/detokenization fixtures; long-prefix request within and beyond context limits |
| 5 | True first-token streaming and timing instrumentation using the named Inferentia I2 streaming host-effect prerequisite and live `norma:tempus` monotonic clock. Record tokenize, verify, prefill, first-token, and completion timestamps without prompt leakage. | 3, 4; Inferentia I2 streaming effect (currently planned and blocked on I1); live Hosts clock provider | Live cold/warm stream with first-token event and monotonic timestamp receipt |
| 6 | Cold/warm qualification and equality receipt. Run identical cold and warm requests, prove prefix prefill was skipped on warm, compare token IDs/text exactly, and record TTFT/capacity/scope/backend. | 2–5; executed Gradus state proof | Committed regime-labeled receipt; no claim from weights-resident-only tests |

## Validation

The closeout gate requires all of the following:

- `faber check .` and the scoped Inferentia integration gate are green.
- Two requests in one tenant/session demonstrate a warm prefix attach; a
  request in a different tenant/session cannot observe or attach that entry.
- Every identity and payload mismatch is rejected or falls back cold according
  to the recorded policy; no mismatch can attach a candidate.
- Capacity and eviction receipts prove bounded memory and deterministic
  lifecycle behavior, including active continuation protection.
- A non-frozen arbitrary prompt and a long-document prefix tokenize and
  detokenize through the real Gradus path; invalid context is rejected.
- The stream exposes first-token timing before completion. Cold and warm runs
  have identical token IDs and text, and the warm receipt proves the reused
  prefix was not prefetched again.
- Responses, logs, and metrics contain no raw token-prefix key or prompt
  content by default.
- The receipt names the single-node backend and explicitly records MD4D as
  out of scope for tiers/routing.

## Ledger

| Unit | Status | Seat | Receipt | Notes |
| --- | --- | --- | --- | --- |
| 1 | pending | — | — | Opaque request/session contract |
| 2 | pending | — | — | Private bounded retention/index lifecycle |
| 3 | pending | — | — | Exact verification and longest-prefix attach |
| 4 | pending | — | — | Arbitrary prompt/tokenizer/detokenizer path |
| 5 | pending | — | — | First-token streaming and clock evidence |
| 6 | pending | — | — | Cold/warm equality and TTFT qualification |

## Open questions

1. **Public handle shape** — default: opaque random/session-scoped handle;
   canonical identity and token-prefix material remain internal. A stable
   external handle must not become a raw token key.
2. **No-candidate behavior** — default: cold fallback. A malformed or
   unauthorized candidate is rejected and never attached; operators may later
   choose fail-closed request behavior only as an explicit API decision.
3. **Scope boundary** — default: tenant plus session. No cross-tenant sharing
   is admitted; same-tenant sharing requires an explicit product policy and
   remains subject to Gradus exact identity verification.
4. **Eviction** — default: byte-budgeted deterministic LRU per tenant, with
   active continuations protected until release. Any alternative must retain a
   bounded budget and an auditable receipt.
5. **Timing boundary** — default: TTFT is the interval from request admission
   to the first emitted generated token, measured by the Hosts monotonic clock.
   The streaming contract must expose that event before completion.
