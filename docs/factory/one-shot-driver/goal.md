# GOAL: one-shot driver — Inferentia exercises the Gradus config/batch/encoding/KV surfaces

**Status**: active — OSD-0 and OSD-1 landed (`8f9bb2c`); serve leftover proven (`ca4bc463`: POST /generate HTTP 200 finish_reason eos; max_prompt 1 → 400); OSD-2 dispatching; OSD-3…OSD-5 gated on OSD-2; OSD-G1 blocked on gradus
**Created**: 2026-09-18
**Campaign:** `inferentia` (`docs/factory/inferentia/CAMPAIGN.md`)
**Source:** operator scope directive 2026-09-18 (via mind task `3c851c35`): "an Inferentia that runs with a single prompt and returns the result … the parts that need work are the things around configuration flags, batch sizes, types of encoding that's used, and KV cache types … the best way to test it is by using one-shot prompts through Inferentia."
**Repos:** `inferentia` (all writes); `gradus` (read/cited; one blocked row)
**Related:** tokenizer serve landed (`3c2aa4b`, discharges `fd205b79`); OSD-0 check-green (`63f9f26`); inventory `eb0fc48c`; pair-synthesis `e7291912` verdict `record_risk` (`59903fc2` × `026d7b78`)

Evidence revisions: inferentia `9ef4add`, gradus `823e37e`. Toolchain: `faber-dev` (install script `radix/scripta/install-faber-dev`). Rebuild it after every radix emitter landing. The PATH `faber` is a stale product binary and must not be used for proofs. `eb0fc48c` is a Vivi handle, not a git SHA.

## Invariant

Every knob Inferentia exposes selects a Gradus-admitted value that the engine
honors end to end, or fails closed with the Gradus typed cause — never a
silently ignored value. A knob whose selection changes nothing observable is a
defect in this goal's own terms.

## Problem

Inferentia is the driver the operator wants to test Gradus with, but at the
current head it cannot even build, let alone run a single prompt, and none of
the four knob families the operator named is reachable:

1. **The tree is check-red.** `faber check .` (radix 1.10.0) fails with 42
   errors, all in `src/main.fab`: 38 `SEM002:qualified_type_not_exported`,
   3 `SEM001:unknown_variant`, 1 `SEM002:qualified_type_prefix_not_namespace`
   — e.g. `gguf_manifest.Cognita`/`Ignota` (`:1090/:1093`) against the
   current `GgmlLayout { Known … Unknown … }` (`gradus/src/model/gguf_manifest.fab:167-175`),
   and `config.default()` (`:1500`), `dense.Lookup` (`:1513`). The retarget
   commit `60345a6` (2026-08-29) wrote these names; gradus has since split
   its leaf type owners (its own last commit is "migrate probas to post-split
   leaf type owners (SEM002 → 0)", gradus green at `89919e7`). Nothing runs —
   no gate, no serve, no live — until this is repaired.
2. **`max_prompt` is pinned to 1 and that breaks every path.** Gradus treats
   `max_prompt` as the prompt-token admission bound
   (`gradus/src/generation/dense.fab:235` — `prompt_ids.length() ≤ g.max_prompt`
   else `"prompt length exceeds max_prompt"`). Inferentia pins it to 1 at
   `src/main.fab:683` (serve requests), `:1880` (serve warm-up), and `:1501`
   (live). The pinned frozen fixture is 9 tokens (`src/main.fab:136-138`), so:
   serve warm-up throws → state failed → every `/generate` answers 503; `live`
   panics; `tests/generate-gate` PASS rows reject identically. The comment at
   `src/main.fab:669-671` ("the engine treat[s it] as the batch size") is
   stale against live Gradus — observed behavior wins.
3. **Encoding policy is hardcoded.** `rope.consecutive_policy()` with θ=100000,
   scale=1.0 at `src/main.fab:1391`. `interleaved_policy`
   (`gradus/src/attention/rope.fab:79`) is implemented end to end — the engine
   consumes it (`gradus/src/attention/gqa.fab:271-280`, applied at `:507`,
   `:578`, `:808`) — but no Inferentia knob reaches it.
4. **Batch is pinned.** `max_prompt` (prefill admission width) is 1; the
   decode-side batch is `AccelerationPolicy.max_block`, and Inferentia only
   ever builds the disabled policy (`to_generation_config` →
   `construct_generation`, `src/main.fab:954-955`, which pins Disabled at
   `gradus/src/generation/config.fab:171-175`). The `context_lookup` path is
   real, verified, multi-row execution (`gradus/src/generation/dense.fab:239-447`,
   `decode_block` at `gradus/src/model/dense.fab:693`) — never exercised.
5. **KV cache type is hardcoded.** Exactly one combination at
   `src/main.fab:1409-1421`: f32/f32, dense, transposed, gqa, classic. Of the
   wide `KVStructure` surface (`gradus/src/cache/structure.fab:113-132`,
   `:199-209`, `:251-271`, `:347-352`, `:388-393`, `:429-434`), nothing else is
   reachable, and — decisively — the non-f32 dtypes are **rejected at
   execution**, not merely unused: the engine's only cache write route is
   `kv.extend` (`gqa.fab:695`), which hard-requires F32 representations
   (`gradus/src/cache/kv.fab:469`, same for `append` at `:445`).
6. **Serve-path encode/decode is the in-flight Hand's unit** (`fd205b79`):
   today `encode_prompt` fails closed to one frozen prompt (`src/main.fab:721-732`)
   and `text` is a space-joined id list (`:743-751`). That Hand fixes both — but
   its own acceptance (`"hello world"` → 200) **cannot pass while (1) and (2)
   stand**. Compile repair plus the unpin are the critical path, not the
   tokenizer.

## Proposal

Make Inferentia a one-shot inference driver: one prompt in, a result out, with
a knob surface that reaches the Gradus surfaces which exist.

| Knob family | Surface | Default | Reachable values (Gradus-admitted) |
| --- | --- | --- | --- |
| Prefill batch | `--max-prompt` (CLI) + `max_prompt` (body) | model context limit (8192) | ≥1, ≤ context (`config.fab:149-150`) |
| Decode batch / acceleration | `--acceleration disabled\|context_lookup`, `--accel-block N` (CLI) + `acceleration`/`accel_block` (body) | disabled | context_lookup is greedy-only (`generation/dense.fab:240-243`) |
| Encoding policy | `--rope-policy consecutive\|interleaved`, `--rope-theta F`, `--rope-scale F` (CLI) | consecutive, 100000.0, 1.0 | both policies implemented end to end (`gqa.fab:271-280`) |
| KV cache type | `--kv-cache f32\|f16\|q8_0\|q4_k` (CLI) | f32 | f32 executes; f16/q8_0/q4_k construct and fail closed at first write (`kv.fab:445/:469`) — blocked on OSD-G1 |

`live` becomes the one-shot entry: `--prompt` (arbitrary text through the
admitted tokenizer), decoded `text=` out. `serve` keeps the same knobs where
request-scoped. Engine-scoped facts (rope, KV structure) are CLI-only; they
are baked into the resident engine/cache at load.

### Non-goals

Per the operator directive, explicitly out of scope — do not lower units for
them, and mark any row that needs them blocked instead:

- Concurrency and request scheduling (single request at a time remains the I1 law)
- Streaming / time-to-first-token work (existing SSE surface is not extended)
- Prefix reuse / cache reuse across requests
- Multi-row and multi-model support (the two Qwen rows stay unadmitted)
- Deployment, packaging, service installation
- Fixing Gradus gaps inside this goal (OSD-G1 and the silent-metadata ledger
  below are recorded, not solved)
- GPU/Metal paths; performance tuning

## Ground truth researched (Gradus surface verdicts)

Which values the engine **honors at execution** vs merely **accepts at
construction** — every row command/file-cited:

| Surface | Construction | Execution | Verdict |
| --- | --- | --- | --- |
| `kv_dtype_f32` (`structure.fab:113`) | admitted | honored — `empty_layers` copies representations into caches (`structure.fab:1219-1230`); `kv.extend` accepts F32 (`kv.fab:469`) | test surface |
| `kv_dtype_f16`/`q8_0`/`q4_k` (`structure.fab:118/123/128`) | admitted (gi4 profile `:515`) | **rejected** — first engine write throws `DtypeMismatch "decoded extend requires F32 K/V representations"` (`kv.fab:469`; append `:445`; engine write route `gqa.fab:695`) | Gradus gap → OSD-G1 (blocked) |
| `dense_structure` (`structure.fab:251`) | admitted | honored — the dense engine's cache loop matches it | test surface |
| `sliding_window`/`compressed_hca`/`indexer` structures (`:256/:262/:271`) | admitted | ignored — no window masking, compression, or partitioning anywhere in the dense engine; indexer layers skipped from cache count (`structure.fab:1200-1204`) | Gradus defect (silent) — ledger only |
| `swa_standard/chunked/symmetric` (`:199-209`) | admitted | ignored (subsumed by the SWA gap above) | Gradus defect (silent) — ledger only |
| `v_layout_transposed/straight` (`:347/:352`) | admitted | ignored — no engine read of `VLayout` (rg: no consumption in `gqa.fab`/`model/dense.fab`/`transformer.fab`) | Gradus defect (silent) — ledger only |
| `sharing_single/gqa` (`:388/:393`) | validated (`:861-869`) | ignored — engine groups heads from `DenseConfig.heads/kv_heads`, not the structure field | Gradus defect (silent) — ledger only |
| `attention_classic/flash` (`:429/:434`) | admitted + profile law (`:831-837`) | ignored — no flash attention path exists in the engine | Gradus defect (silent) — ledger only |
| `profile_gi4/cuda` (`:514/:519`) | gi4 admitted; cuda rejected at construction (`:846`) | n/a | construction-time only |
| `consecutive_policy` (`rope.fab:74`) | admitted | honored — `gqa.fab:271-280` applied at `:507/:578/:808` | test surface |
| `interleaved_policy` (`rope.fab:79`) | admitted | honored — same math path, different pair split | test surface |
| rope θ / scale (`rope.fab:119`) | admitted | honored (rotation table) | test surface |
| `max_prompt` | validated (`config.fab:149-150`) | honored as prompt-length admission bound (`generation/dense.fab:235`) | test surface — broken by the Inferentia pin |
| acceleration `disabled` | admitted | honored — scalar decode loop (`generation/dense.fab:257-277`) | test surface |
| acceleration `context_lookup` | admitted | honored — `lookup_candidates` + multi-row `decode_block` + `commit_dense_block` (`generation/dense.fab:279-447`), greedy-only guard (`:240-243`) | test surface |
| sampling fields, seed, context, eog_ids | validated (`config.fab:145-169`) | honored | plumbed today (see coverage table in `delivery.md`) |

Additional found defect: `live` compares its output to `golden_tokens_16`
under `generate_dense` = **eog_stop** (`src/main.fab:1509`, golden at `:1026-1028`),
but that golden is the **ignore_eos** continuation (generate-gate header:
eog_stop greedy continuation is `[30, 2]`; `decoder.sample_logits` suppresses
EOG only under ignore_eos, `gradus/src/generation/decoder.fab:140-144`). Masked
today by the max_prompt panic; OSD-2 owns the resolution.

## Reference packet

- `inferentia/src/main.fab` — all knob seams: `parse_cli` :1579, `print_help` :1556,
  `json_parse_generate_body` :484, `build_generate_config` :672 (pin :683),
  `to_generation_config` :954, `load_resident_weights` :1355 (rope :1391,
  DenseConfig :1398-1403, KV structure :1409-1421), `run_generate` :1446,
  `live_run` :1463 (config :1501), `serve` :1851 (warm-up pin :1880),
  `encode_prompt` :725, `tokens_text` :743.
- `gradus/src/generation/config.fab` — `AccelerationPolicy` :77-82,
  `construct_acceleration` :86-92, `GenerationConfig` :114-125,
  `construct_generation_with_policy` :145-169, `construct_generation` :171-175,
  `support_flags` :195-198.
- `gradus/src/generation/dense.fab` — admission :233-236, greedy guard :239-243,
  disabled loop :257-277, context_lookup block path :279-447.
- `gradus/src/model/dense.fab` — `decode_block` :693, `prefill_cached` :790,
  `empty_caches` :593.
- `gradus/src/attention/gqa.fab` — `_interleaved` :271-280, applications
  :507/:578/:808, cache write :695.
- `gradus/src/cache/kv.fab` — F32-only decoded writes :445, :469.
- `gradus/src/cache/structure.fab` — factories :113-132/:199-209/:251-271/
  :347-352/:388-393/:429-434, profiles :514-519, `empty_layers` :1219-1230.
- `gradus/src/tokenizer/bpe.fab` — `build` :282, `decode` :469, `tokenize` :578.
- Model row: `/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf`
  (sha256 `2fa3f013…ac9c2`, `src/main.fab:1024-1026`; 270590880 bytes per
  verification task `55bfe796`).
- One-shot test recipes: `recipes.md` (this directory) — the operator-facing
  artifact; first-class, not an appendix.

## Constraints and invariants

- Gradus is the provider (campaign ruling 2615e6a9): reusable ML semantics stay
  in `gradus:*`; Inferentia never compensates for a missing primitive.
- Fail closed everywhere: unknown knob values are typed usage errors; a knob
  value Gradus cannot execute surfaces Gradus's typed cause verbatim.
- Deterministic by default: greedy (temperature 0, top_k 0, top_p 1, min_p 0)
  + seed ≥ 1, so every recipe's expected observation is exact.
- One request at a time (I1 law) — `max_prompt` is prefill token width, never
  a request count.
- The fixed `/generate` body schema stays fail-closed (unknown fields reject);
  new body fields follow the existing duplicate/type-reject pattern.

## Architecture direction

Knobs are thin: `ServeConfig` (CLI) and `GenerateRequest`/`GenerateConfig`
(body) gain fields that map 1:1 onto admitted Gradus constructors —
`construct_rope_config`, `construct_kv_structure` inputs,
`construct_acceleration` + `construct_generation_with_policy`. No new
abstraction, no per-request engine rebuild for load-scoped facts (rope/KV
structure are baked into the resident model at load, like today). No
compatibility layer for values Gradus rejects — the typed cause is the product
behavior. Ownership: all rows in `inferentia`; the one Gradus row (OSD-G1) is
blocked and named, not shouldered.

## Units (lowering sketch — refined in `delivery.md`)

| Unit | Scope | Depends on | Hand evidence |
| --- | --- | --- | --- |
| OSD-0 | compile repair — repoint the 42 dangling gradus-qualified names | — | none |
| OSD-1 | unpin `max_prompt` + `--max-prompt`/body field | OSD-0; tokenizer serve `3c2aa4b` (landed); emit-chain build-green | none |
| OSD-2 | `live --prompt` one-shot entry (arbitrary prompt, decoded text, stop-policy/golden fix) | OSD-1 | none |
| OSD-3 | rope knobs (`--rope-policy/--rope-theta/--rope-scale`) | OSD-2 | none |
| OSD-4 | KV cache type knob (`--kv-cache`) | OSD-2 | none |
| OSD-5 | acceleration knobs (`--acceleration/--accel-block` + body fields) | OSD-2 | none |
| OSD-G1 | (gradus, BLOCKED) non-F32 KV engine write/read path | — | none |

## Validation

The goal proves done by executing `recipes.md` end to end at the landed head:
each recipe is one command with an exact expected observation and an explicit
broken-observation (what would count as the surface being broken rather than
merely unused). Suite-green is not enough — the falsifiable oracle per recipe
is the gate (default-rope golden match, interleaved deterministic divergence,
context_lookup token-identity with disabled, typed rejections for
sampled-acceleration and non-f32 KV). Closeout also requires the Gradus gap
ledger below to remain accurate against the then-current gradus head.

## Delivery checklist

| Check | Enforced by |
| --- | --- |
| Status line stays one machine-parseable clause | radix factory status audit (stage 1) |
| Every unit's done_when is exactly one runnable command | Mind dispatch check against `delivery.md` |
| Recipes runnable verbatim from the rendered doc | planner verification discipline (commands extracted and executed before report) |
| No knob added for a construction-only Gradus value | this goal's Invariant + gap ledger |

## Ledger

| Unit | Status | Seat | Receipt | Notes |
| --- | --- | --- | --- | --- |
| OSD-0 compile repair | done | `a343b98a` | `63f9f26` | check-green only; the `build .` leg of the written done_when could not have passed (emit chain postdates this commit) |
| OSD-1 unpin max_prompt + knob | done | `cb433109` | `8f9bb2c` / `ca4bc463` | POST /generate 200 finish_reason; `--max-prompt` body bound 400 |
| OSD-2 live one-shot entry | in flight | — | — | after serve leftover |
| OSD-3 rope knobs | pending | — | — | |
| OSD-4 kv-cache knob | pending | — | — | f32 oracle only |
| OSD-5 acceleration knobs | pending | — | — | |
| OSD-G1 non-F32 KV execution (gradus) | blocked | — | — | needs its own gradus goal; not dispatched here |

Gradus gap ledger (construction-admitted, execution-ignored or rejected —
Gradus defects, recorded not solved): non-F32 KV dtypes (rejected, `kv.fab:445/:469`);
`v_layout`; `AttentionFamily.Flash`; `KvSharing` field; SWA/HCA/Indexer layer
structures; SWA kinds (all silently ignored — see ground-truth table).

## Open questions

1. Body schema for `max_prompt`/`acceleration` — default recorded: add both as
   body fields with the existing duplicate/type-reject pattern (the operator
   asked for "CLI and request knobs"). Revisit only if the D3 freeze is ruled
   binding.
2. Live golden compare — default recorded: golden 16-token compare applies
   only under an ignore-eos stop; default live prints `ids=`/`text=` and PASS
   only for the frozen prompt's eog_stop continuation `[30, 2]`.
3. Whether non-f32 `--kv-cache` should fail fast before model load — default:
   no; surface Gradus's typed cause at first generation (honest, and the recipe
   depends on observing it).
4. Rope θ from GGUF metadata (`rope.freq_base`) instead of CLI default — needs
   a float metadata accessor Gradus does not export today (only
   `text`/`number`, `gguf_manifest.fab:629-637`). Out of this goal; CLI knob
   suffices for the driver.

## Stop conditions

- If `fd205b79` lands materially different from its assignment (e.g. no
  `tokenizator.decode` in the response), OSD-2's decode seam needs re-checking
  before dispatch.
- If the PATH `faber` (1.8.0) is not replaced or Hands are not pointed at the
  radix-built 1.10.0 binary, every proof command fails for environment
  reasons — fix the toolchain before dispatching, not around it.
- If Gradus moves the admission or acceleration seams cited above, re-verify
  the citations before dispatching the affected row.
- If a row's done_when cannot pass without a non-goal (concurrency, streaming,
  multi-model), mark it blocked with the cause — do not admit the non-goal.
