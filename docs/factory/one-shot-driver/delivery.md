# DELIVERY: one-shot driver — unit graph

**Goal:** `docs/factory/one-shot-driver/goal.md` (planned; this lowering)
**Evidence revisions:** inferentia `83693e0`, gradus `89919e7`
**Model row (absolute, packet-independent):**
`MODEL=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf`
**Toolchain (verified this session):** the PATH `faber` is a stale 1.8.0 that
fails every checkout (PKG001/PARSE001); the working authority is the
radix-built binary. Every command below sets
`FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber` (1.10.0;
gradus checks green under it). If Mind deploys 1.10.0 to PATH, bare `faber`
supersedes — until then proofs must use the absolute path.
**Command convention:** every `done_when` below is ONE `bash -ec` command,
run from the inferentia repo root of whatever checkout you are in (main or
packet). It builds, runs, and decides pass/fail by its own exit code.

## Interpreted theme / problem

Inferentia cannot build at head (42 dangling gradus-qualified names from the
2026-08-29 retarget), cannot run one prompt (the `max_prompt=1` pin), and the
operator's four knob families (config flags, batch, encoding, KV cache) have
no reachable surface. Lower the goal into a compile-repair unit, knob-wiring
units, and one blocked Gradus dependency. The in-flight Hand `fd205b79`
(serve tokenizer encode + detokenized response) is NOT duplicated here;
OSD-0 + OSD-1 are what make its acceptance passable.

## Normalized spec (delivery-sized outcome)

`inferentia live --prompt "<arbitrary text>" [--max-tokens N] [--max-prompt N]
[--rope-policy …] [--rope-theta F] [--rope-scale F] [--kv-cache …]
[--acceleration …] [--accel-block N] --model $MODEL` runs one prompt through
the admitted tokenizer, the resident engine, and the selected Gradus surfaces,
prints `ids=` and decoded `text=`, and fails closed with Gradus typed causes.
Serve exposes the request-scoped subset (`max_prompt`, `acceleration`,
`accel_block`) as body fields alongside the existing eight.

## Repo-aware baseline

- **Head is check-red (verified):** `$FABER check .` → exit 1, 42 errors, all
  in `src/main.fab` — 38 `SEM002:qualified_type_not_exported`, 3
  `SEM001:unknown_variant`, 1 `SEM002:qualified_type_prefix_not_namespace`.
  Confirmed example pairs: `gguf_manifest.Cognita`/`Ignota` (`:1090/:1093`)
  vs current `GgmlLayout { Known …, Unknown … }`
  (`gradus/src/model/gguf_manifest.fab:167-175`); other sites include
  `config.default()` (`:1500`), `dense.Lookup` (`:1513`). Written by retarget
  `60345a6` (2026-08-29); gradus split its leaf type owners afterward.
- Serve knob seams: `parse_cli` (`src/main.fab:1579-1667`, unknown-option
  reject at `:1645`), `print_help` (`:1556`), `json_parse_generate_body`
  (`:484-646`; fixed schema, duplicate/type rejects), `build_generate_config`
  (`:672-691`, pin at `:683`), `to_generation_config` (`:954-956`).
- Engine construction: `load_resident_weights` (`:1355-1437`) — rope at
  `:1389-1393`, `DenseConfig` at `:1398-1403`, KV structure at `:1408-1424`,
  engine at `:1425`.
- Generation entry: `run_generate` (`:1446-1461`), `live_run` (`:1463-1536`,
  config pin at `:1501`), `serve` warm-up (`:1877-1904`, pin at `:1880`).
- Gradus constructors to map onto: `construct_rope_config`
  (`rope.fab:119`), `construct_kv_structure` (`structure.fab:894-897`),
  `construct_acceleration` (`config.fab:86-92`),
  `construct_generation_with_policy` (`config.fab:145-169`).
- Toolchain constraint (recorded `src/main.fab:709-711`): the MIR stepper
  cannot lower a conditional inside a `cape` block wrapping a library-provider
  call — keep conditional/fallback shapes in their own functions.
- Existing knob coverage (all of `GenerationConfig`, `config.fab:114-125`):

| Gradus field | CLI | Body | State at head |
| --- | --- | --- | --- |
| `context` | `--context` (0 → 8192) | — | plumbed |
| `max_prompt` | — | — | **pinned 1, broken** → OSD-1 |
| `max_tokens` | `--max-tokens` | `max_tokens` | plumbed |
| `seed` | `--seed` | `seed` | plumbed |
| `temperature` | — | `temperature` | plumbed (body) |
| `top_k` / `top_p` / `min_p` | — | `top_k`/`top_p`/`min_p` | plumbed (body) |
| `repetition_penalty` | — | `repeat_penalty` | plumbed (body) |
| `eog_ids` | — (tokenizer-derived, `:1357`) | — | correct by design |
| `acceleration` | — | — | **absent** → OSD-5 |
| rope θ/scale/policy | — | — | **hardcoded** → OSD-3 |
| KV dtype | — | — | **hardcoded** → OSD-4 |

No dead knobs exist (every CLI/body field above flows into
`construct_generation`). The unreachable fields are exactly `max_prompt` and
`acceleration`, plus the engine-scoped rope/KV facts.

## Hand unit graph

All rows write `inferentia/src/main.fab` only → **serial dispatch in row
order** (same-file lanes); logical deps are as marked. Row verdicts at the
end of each row: READY / NOT READY with the evidence used.

---

### OSD-0 — compile repair: repoint the dangling gradus-qualified names

- **Outcome:** one logical change — `src/main.fab` compiles against
  gradus `89919e7` under faber 1.10.0 with zero check errors, with no
  behavior change intended beyond naming. Resolve all 42 sites (38
  `qualified_type_not_exported`, 3 `unknown_variant`, 1
  `qualified_type_prefix_not_namespace`) by mapping each dangling name onto
  the current gradus leaf-export surface — the reference pattern is gradus's
  own "post-split leaf type owners" migration (gradus HEAD commit
  `89919e7`): types come from the leaf that owns them, spelled as that leaf
  now exports them. Confirmed example: `Cognita`→`Known`,
  `Ignota`→`Unknown` (`gguf_manifest.fab:167-175`). Where a name has no
  current equivalent, use the leaf's exported replacement — never invent a
  local shim (gradus owns the semantics; ruling 2615e6a9).
- **Write scope:** `inferentia/src/main.fab` (plus `inferentia/faber.lock`
  only if a dependency repoint is required)
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; $FABER check . && $FABER build .'
```
- **Sanity:** `bash -ec '/Users/ianzepp/work/faberlang/radix/target/debug/faber check . 2>&1 | grep -c "error\[" | grep -qx 0'`
- **Depends on:** — (nothing; this is the first row)
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** medium
  (mechanical, but 42 sites; a mis-mapped name is a silent behavior change —
  the done_when proves compile only, the golden gates prove behavior)
- **Non-goals:** no behavior changes, no knob work, no gradus edits.
- **Falsifiable oracle:** before: `check` exits 1 with 42 errors; after:
  exit 0 and `faber build .` produces `./target/debug/inferentia`. The
  existing gate packages (`tests/generate-gate` etc.) then run — their PASS
  rows will still hit the `max_prompt` rejection until OSD-1 (that is
  OSD-1's oracle, not a defect of this row).
- **Verdict: READY** — evidence: error inventory command-derived and pasted
  above; confirmed rename pair cited; reference migration named.

---

### OSD-1 — unpin `max_prompt`; add `--max-prompt` CLI + `max_prompt` body field

- **Outcome:** one logical change — the prefill admission bound becomes a real
  knob with a working default. Replace the pinned `magna_promptus = 1` at
  `:683`, `:1880`, and `:1501` with the configured value; default = model
  context limit (8192) when neither body nor CLI sets it; precedence body >
  CLI > default (the existing D2 pattern, `:668`). Add `--max-prompt N`
  (validate ≥ 1, like `--max-tokens`) to `parse_cli` + `print_help`; add the
  `max_prompt` body field to `json_parse_generate_body` + `GenerateRequest`
  with the existing duplicate/type-reject pattern; extend
  `GenerateConfig`/`build_generate_config` accordingly. Rewrite the stale
  comment at `:669-671` (gradus treats `max_prompt` as the prompt-token
  admission bound, `generation/dense.fab:235` — not a request batch).
- **Write scope:** `inferentia/src/main.fab`
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; $FABER build . && ./target/debug/inferentia serve --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --port 18210 > /tmp/osd1.log 2>&1 & SPID=$!; for i in $(seq 1 60); do grep -q "generation ready" /tmp/osd1.log && break; sleep 5; done; grep -q "generation ready" /tmp/osd1.log && curl -sS -X POST http://127.0.0.1:18210/generate -H "content-type: application/json" --data "{\"prompt\":\"The quick brown fox jumps over the lazy dog\",\"max_tokens\":4}" | grep -q "\"finish_reason\""; RC=$?; kill $SPID 2>/dev/null; exit $RC'
```
- **Sanity:** `bash -ec '/Users/ianzepp/work/faberlang/radix/target/debug/faber check . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf 2>&1 | grep -v "prompt length exceeds max_prompt"'`
  (live no longer dies on the admission bound; its golden/stop mismatch is
  OSD-2's row, so only the max_prompt cause is asserted absent here)
- **Depends on:** OSD-0 (compile); `fd205b79` landing (same file; its
  encode/decode edits sit in the same functions this row touches around
  `build_generate_config` callers)
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** low
- **Non-goals:** no acceleration/rope/KV changes; no live-mode restructure.
- **Falsifiable oracle:** before the change the done_when's curl answers 503
  (state failed at warm-up, `:1896-1902`); after, warm-up reaches
  "generation ready" and the frozen 9-token prompt returns 200. If `--max-prompt 1`
  is passed explicitly, the same curl answers 400 `"prompt length exceeds
  max_prompt"` — the admission surface live, not decorational.
- **Verdict: READY** — evidence: pin sites cited; admission rule cited; D2
  precedence pattern exists in-file; CLI validation pattern exists in-file.

---

### OSD-2 — `live` one-shot entry: `--prompt`, decoded text, stop-policy fix

- **Outcome:** one logical change — `live` becomes the one-shot driver. Accept
  `--prompt "<text>"` (default: the frozen fixture text). Tokenize the given
  prompt through the admitted tokenizer (the `live_build_tokenizer`/
  `live_tokenize` pair already at `:1306-1322`, already used in `live_run:1487`);
  the frozen-golden tokenize check (`:1489-1494`) applies only when the prompt
  equals `frozen_prompt_text()`. Print `ids=` (space-joined) and `text=` via
  `tokenizator.decode` (`gradus/src/tokenizer/bpe.fab:469`) — fail closed on
  decode error. Wire `ServeConfig.max_tokens`/`--max-tokens` into live's
  generation config (today hardcoded 16 at `:1501`). Fix the stop-policy/golden
  mismatch: default live runs `eog_stop` and its printed oracle for the frozen
  prompt is the `[30, 2]` continuation (generate-gate header fact); the
  16-token `golden_tokens_16` compare (`:1526-1535`) moves under an explicit
  `--ignore-eos` flag that selects `decoder.ignore_eos()`
  (`gradus/src/generation/decoder.fab:89`). Respect the MIR-stepper cape
  constraint (`:709-711`): keep conditional/fallback shapes out of `cape`
  blocks wrapping provider calls.
- **Write scope:** `inferentia/src/main.fab`
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; $FABER build . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --prompt "hello world" --max-tokens 8 2>&1 | tee /tmp/osd2.log | grep -E "^text=..+" && grep -E "^ids=..+" /tmp/osd2.log'
```
- **Sanity:** `bash -ec '/Users/ianzepp/work/faberlang/radix/target/debug/faber check . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf 2>&1 | tail -3'`
  (frozen default: prints the `[30, 2]` continuation shape, no panic)
- **Depends on:** OSD-1 (a >1-token prompt panics until the unpin)
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** medium
  (touches the golden oracle; the `[30, 2]` default expectation must be
  confirmed against the run before committing the test change)
- **Non-goals:** no knob families beyond prompt/max-tokens/ignore-eos; no
  serve-path changes (`fd205b79` owns those).
- **Falsifiable oracle:** `--prompt "hello world"` (2+ tokens) produces a
  non-empty decoded `text=` that is NOT a space-joined integer list; at head
  the same invocation panics on `prompt length exceeds max_prompt`, and even
  post-OSD-1 without this row live still tokenizes only the frozen fixture.
- **Verdict: READY** — evidence: tokenizer pair cited in-file; decode export
  cited; stop-policy semantics cited (`decoder.fab:106-144`).

---

### OSD-3 — rope knobs: `--rope-policy`, `--rope-theta`, `--rope-scale`

- **Outcome:** one logical change — the encoding policy becomes selectable.
  Add the three CLI flags (policy validated as `consecutive|interleaved`;
  theta/scale validated positive-finite to mirror `construct_rope_config`'s
  contract, `rope.fab:119-121` — invalid values are typed usage errors, not
  silent clamps). Thread them through `ServeConfig` → `load_resident_weights`
  rope construction (`:1389-1393`, replacing the hardcoded
  `100000.0/1.0/consecutive`). Defaults preserve today's exact values, so the
  golden path is bit-identical.
- **Write scope:** `inferentia/src/main.fab`
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; P="The quick brown fox jumps over the lazy dog"; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep "^ids=" > /tmp/osd3a && $B live --model $M --prompt "$P" --max-tokens 8 --rope-policy interleaved 2>&1 | grep "^ids=" > /tmp/osd3b && ! cmp -s /tmp/osd3a /tmp/osd3b && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep -qE "^ids=30 2( |$)"'
```
- **Sanity:** `bash -ec '/Users/ianzepp/work/faberlang/radix/target/debug/faber check . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --rope-theta 0 2>&1 | grep -i "rope"'`
  (typed usage error, non-zero exit — theta 0 is invalid per `rope.fab:121`)
- **Depends on:** OSD-2 (the one-shot entry the oracle runs through)
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** low
- **Non-goals:** no per-request rope (engine-scoped, baked at load);
  no metadata-derived theta (open question 4 in the goal).
- **Falsifiable oracle:** interleaved must produce a **deterministically
  different** continuation than consecutive on the same prompt/seed
  (SmolLM2 is llama-arch, trained consecutive — `rope.fab:56-58` — so
  divergence is the expected observation). Identical output would prove the
  knob is ignored = defect. Default run must reproduce the `[30, 2]`
  continuation (no regression).
- **Verdict: READY** — evidence: hardcode site cited; both policies
  implemented end to end (`gqa.fab:271-280` applied `:507/:578/:808`);
  validation contract cited.

---

### OSD-4 — KV cache type knob: `--kv-cache f32|f16|q8_0|q4_k`

- **Outcome:** one logical change — the KV cache dtype becomes selectable.
  Add the CLI flag (validated against the four Gradus names,
  `structure.fab:113-132`; unknown → typed usage error). Map the name to the
  `kv_dtype_*` factory pair and thread through `load_resident_weights`
  structure construction (`:1413-1419`, replacing the hardcoded
  `kv_dtype_f32()/kv_dtype_f32()`). The knob sets K and V together. f32 is the
  only value that can complete a generation today: f16/q8_0/q4_k construct
  (gi4-admitted, `structure.fab:515`) and then fail closed at the first cache
  write with Gradus's typed cause (`kv.fab:445/:469` — engine write route
  `gqa.fab:695`). That typed failure is the documented, expected observation —
  do not catch, map, or soften it.
- **Write scope:** `inferentia/src/main.fab`
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; $FABER build . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --kv-cache f32 2>&1 | grep -qE "^ids=30 2( |$)"'
```
- **Sanity:** `bash -ec '/Users/ianzepp/work/faberlang/radix/target/debug/faber check . && ./target/debug/inferentia live --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --kv-cache f16 2>&1 | grep "requires F32 K/V representations"'`
  (the Gradus typed cause surfaces verbatim; a 200-equivalent success or a
  different silent behavior would be the defect)
- **Depends on:** OSD-2; **blocked extension:** non-f32 *execution* blocked on
  OSD-G1 (Gradus) — this row's done_when deliberately uses f32 only.
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** low
- **Non-goals:** no v-layout/sharing/attention-family/SWA knobs — those
  Gradus values are construction-only (goal gap ledger); a knob for them
  would lie.
- **Falsifiable oracle:** `--kv-cache f32` reproduces the default golden
  continuation bit-for-bit (the knob is a no-op at the default value);
  `--kv-cache f16` fails with exactly `"decoded … requires F32 K/V
  representations"`. Silent success under f16 would mean Gradus ignored the
  declared dtype = defect (that is the "broken rather than merely unused"
  test).
- **Verdict: READY** — evidence: hardcode site cited; F32-only write route
  cited; gi4 admission set cited.

---

### OSD-5 — acceleration knobs: `--acceleration`, `--accel-block` + body fields

- **Outcome:** one logical change — the decode batch/acceleration policy
  becomes selectable. Add `--acceleration disabled|context_lookup` and
  `--accel-block N` (1 ≤ N, used as min_block = max_block) to the CLI, and
  `acceleration`/`accel_block` body fields to the fixed `/generate` schema
  (existing duplicate/type-reject pattern). Build the policy with
  `construct_acceleration(POLICY_VERSION …)` and the config with
  `construct_generation_with_policy` (`config.fab:86-92`, `:145-169`) —
  `to_generation_config` (`:954`) switches to the policy-carrying
  constructor. Defaults preserve today's exact behavior (disabled).
- **Write scope:** `inferentia/src/main.fab`
- **Done when (one command; exit 0 = pass):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; P="The quick brown fox jumps over the lazy dog"; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep "^ids=" > /tmp/osd5a && $B live --model $M --prompt "$P" --max-tokens 8 --acceleration context_lookup --accel-block 4 2>&1 | grep "^ids=" > /tmp/osd5b && cmp -s /tmp/osd5a /tmp/osd5b'
```
- **Sanity:** `bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; $FABER build . && ./target/debug/inferentia serve --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf --port 18211 --acceleration context_lookup > /tmp/osd5.log 2>&1 & SPID=$!; for i in $(seq 1 60); do grep -qE "generation ready|failed" /tmp/osd5.log && break; sleep 5; done; curl -sS -X POST http://127.0.0.1:18211/generate -H "content-type: application/json" --data "{\"prompt\":\"The quick brown fox jumps over the lazy dog\",\"max_tokens\":4,\"temperature\":0.7}" | grep "sampled acceleration is not supported"; RC=$?; kill $SPID 2>/dev/null; exit $RC'
```
- **Depends on:** OSD-2 (live oracle); body-field half also depends on OSD-1's
  schema-extension pattern (same parser function — serial same-file dispatch
  already enforces order).
- **Owning repo:** inferentia — **Integrable:** yes — **Risk:** medium
  (touches the generation-loop selection via config; equivalence oracle must
  hold for every block size)
- **Non-goals:** no speculative decoding provider work (`speculative.fab`
  admission seams exist but are not this row); no sampled acceleration
  (Gradus rejects it — the guard is the test surface, `generation/dense.fab:240-243`).
- **Falsifiable oracle:** greedy `context_lookup` must be **token-identical**
  to greedy `disabled` on the same prompt/seed (the verify path accepts only
  matching candidates and falls back otherwise, `generation/dense.fab:279-447`).
  Divergence or crash = defect. Sampled params + context_lookup must answer
  the typed 400 `"sampled acceleration is not supported"` — silent greedy
  fallback would be a defect.
- **Verdict: READY** — evidence: policy constructors cited; engine paths
  cited; greedy guard cited; body/parser pattern in-file.

---

### OSD-G1 — (GRADUS, BLOCKED) non-F32 KV cache execution path

- **Outcome:** the Gradus engine gains a quantized/f16 KV write/read path so
  `--kv-cache f16|q8_0|q4_k` can execute (today: `kv.append`/`kv.extend`
  decoded routes are F32-only, `kv.fab:445/:469`; encoded routes exist
  (`append_encoded`/`extend_encoded`, `kv.fab:516+`) with **no engine
  caller**; the engine writes via `gqa.fab:695` only).
- **Write scope (when unblocked):** `gradus/src/cache/kv.fab`,
  `gradus/src/attention/gqa.fab`, `gradus/src/model/dense.fab` + leaf probas.
- **Done when:** not lowerable as a command until Gradus scopes it — this row
  is **NOT READY** and needs its own gradus goal-forge (design fork:
  quantize-on-write in `gqa`, vs a cache-side codec seam, vs engine-side
  dequant-on-read; owner: gradus).
- **Depends on:** — — **Owning repo:** gradus — **Integrable:** n/a
- **Risk:** high (numeric-equivalence law for quantized KV has no oracle yet).
- **Verdict: NOT READY (blocked)** — evidence: F32-only require lines cited;
  no engine caller for the encoded routes (rg over `gradus/src/`). Mind
  registers the gap; it does not gate OSD-4's f32 oracle.

## Integration / merge gate

All rows are individually integrable (each leaves default behavior
bit-identical to head — OSD-0 changes naming only). Same-file serial dispatch
makes conflicts unlikely; if merge sees overlap, `factory/merge` aggregates in
row order OSD-0 → OSD-1 → OSD-2 → {OSD-3, OSD-4, OSD-5}.

## Lane-owned validation (named once — never copied onto a Hand)

- Lint: stages 1–2 on the integrated inferentia tree (radix ladder).
- Test: inferentia inline tests (`$FABER test .`) + gate packages
  (`tests/admission-gate`, `tests/generate-gate`, `tests/model-gate`,
  `tests/process-exit`) on the integrated tree — note `generate-gate` PASS rows
  also need the OSD-1 unpin to hold at the integrated head.
- Recipe suite: `recipes.md` executed end to end at the integrated head
  (verification seat, not the implementing Hands).

## Open questions for Mind

1. Register the goal before dispatch:
   `vivi goal add --project /Users/ianzepp/work/faberlang --path inferentia/docs/factory/one-shot-driver/goal.md --label one-shot-driver --for mind`
2. **Toolchain:** PATH `faber` is 1.8.0 and fails every checkout
   (PKG001/PARSE001); the working binary is
   `/Users/ianzepp/work/faberlang/radix/target/debug/faber` (1.10.0). Deploy
   1.10.0 to PATH (a radix/faber release concern) or point every Hand at the
   absolute path — the in-flight tasks' bare `faber` invocations currently
   resolve to the broken one.
3. Confirm `fd205b79`'s landing before dispatching OSD-1 (same file, adjacent
   seams); its acceptance itself needs OSD-0 + OSD-1 — decide merge order with
   the Hand seat or fold both into that lane's merge if it lands first.
4. OSD-2's `[30, 2]` default expectation comes from the generate-gate header
   comment — the Hand must confirm against a live run before hardcoding the
   test (medium risk noted on the row).
5. Body fields `max_prompt`/`acceleration` extend the frozen D3 schema — the
   default (add them, per the operator's "CLI and request knobs") is recorded
   in goal open question 1; overrule before OSD-5 dispatch if D3 must freeze.
