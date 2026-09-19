# One-shot test recipes — exercising the Gradus surfaces through Inferentia

**Goal:** `docs/factory/one-shot-driver/goal.md` · **Lowering:** `delivery.md`
**Evidence revisions:** inferentia `83693e0`, gradus `89919e7`
**Model row:** `/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf`
(sha256 `2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2`,
`src/main.fab:1024-1026`)

Conventions every recipe shares:

- `FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber` (1.10.0 —
  the PATH `faber` is a stale 1.8.0 that fails every checkout; verified this
  session).
- `B=./target/debug/inferentia`; `M=$MODEL` as above; run from the inferentia
  repo root. Each recipe is one `bash -ec` command deciding pass/fail by exit
  code.
- Deterministic law: greedy by default (temperature 0, top_k 0, top_p 1,
  min_p 0), seed 1 — expected observations are exact, not statistical.
- "Runnable when" names the landing row; at head **no recipe runs**: the tree
  is check-red (42 errors, OSD-0) and `max_prompt=1` rejects every prompt over
  one token including the frozen 9-token fixture (OSD-1). Runtime confirmation
  of that head state is verification handle `55bfe796`'s in-flight job; the
  code paths are deterministic (`generation/dense.fab:235`).

The frozen fixture prompt (all recipes): `The quick brown fox jumps over the
lazy dog` → pinned ids `[504, 2365, 6354, 16438, 27003, 690, 260, 23790,
2767]` (`src/main.fab:131-138`). Its greedy eog_stop continuation is
`[30, 2]` (generate-gate header fact); the 16-token golden
`golden_tokens_16` (`:1026-1028`) is the **ignore_eos** continuation.

## R1 — KV cache dtype: f32 (the only executing value)

- **Knob setting:** `--kv-cache f32` (also the default)
- **Runnable when:** OSD-2 landed (knob itself lands with OSD-4; the f32 path
  is bit-identical to today's default, so this recipe doubles as the
  no-regression oracle for OSD-4)
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --kv-cache f32 2>&1 | grep -E "^ids=30 2( |$)"'
```
- **Expected observation:** exit 0; `ids=30 2` — the dtype knob at its
  default value is a no-op against the golden continuation (structure
  construction sites `src/main.fab:1413-1419` → `structure.fab:894` →
  `empty_layers` `:1219-1230` → F32-decoded caches that `kv.extend` accepts,
  `kv.fab:469`).
- **Broken, not merely unused:** any panic, any `DtypeMismatch`, or a
  different continuation — the default path must be bit-stable.

## R2 — KV cache dtype: f16 / q8_0 / q4_k (fail-closed execution gap)

- **Knob setting:** `--kv-cache f16` (repeat for `q8_0`, `q4_k`)
- **Runnable when:** OSD-4 landed
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --kv-cache f16 2>&1 | grep "requires F32 K/V representations"'
```
- **Expected observation:** the Gradus typed cause surfaces verbatim —
  `"decoded append requires F32 K/V representations"`
  (`gradus/src/cache/kv.fab:445`) or the `extend` spelling (`:469`) at the
  first cache write (engine route `gqa.fab:695`), after the weights load.
  This is the **known gap OSD-G1**, honestly reported, not worked around.
- **Broken, not merely unused:** a *successful* generation under f16 with
  output identical to f32 — that would mean Gradus constructed the cache with
  a declared f16 representation and then silently wrote/reading F32 decode
  paths (or ignored the field), i.e. the dtype is decorative. Also broken: an
  untyped crash, or an Inferentia-mapped error that hides Gradus's cause.

## R3 — Encoding policy: consecutive (default, no-regression)

- **Knob setting:** `--rope-policy consecutive` (also the default; θ=100000,
  scale=1.0)
- **Runnable when:** OSD-2 landed (knob lands with OSD-3)
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M 2>&1 | grep -E "^ids=30 2( |$)"'
```
- **Expected observation:** `ids=30 2` — the SmolLM2 row's trained recipe
  (llama-arch consecutive pairs, `rope.fab:56-58`) reproduces the golden
  continuation; the hardcoded values at `src/main.fab:1391` move into knobs
  without changing behavior.
- **Broken:** any different continuation or panic.

## R4 — Encoding policy: interleaved (divergence is the proof)

- **Knob setting:** `--rope-policy interleaved`
- **Runnable when:** OSD-3 landed
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; P="The quick brown fox jumps over the lazy dog"; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep "^ids=" > /tmp/r4a && $B live --model $M --prompt "$P" --max-tokens 8 --rope-policy interleaved 2>&1 | grep "^ids=" > /tmp/r4b && ! cmp -s /tmp/r4a /tmp/r4b'
```
- **Expected observation:** the two `ids=` lines **differ deterministically**
  (same prompt, seed, greedy). Gradus honors the policy end to end —
  `_interleaved` (`gqa.fab:271-280`) changes the rotation pair split at
  `:507/:578/::808`. SmolLM2 was trained consecutive, so interleaved rotation
  computes a different (wrong-for-this-model, but well-defined) continuation.
- **Broken, not merely unused:** identical output under both policies — that
  would prove the knob (or Gradus's policy consumption) is ignored, the exact
  "silently accepted at construction" defect this goal exists to catch.

## R5 — Encoding policy: θ and scale (divergence is the proof)

- **Knob setting:** `--rope-theta 1000000.0` (a Qwen-row value,
  `docs/factory/inferentia/i1-discovery.md:76`); repeat with
  `--rope-scale 0.5`
- **Runnable when:** OSD-3 landed
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; P="The quick brown fox jumps over the lazy dog"; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep "^ids=" > /tmp/r5a && $B live --model $M --prompt "$P" --max-tokens 8 --rope-theta 1000000.0 2>&1 | grep "^ids=" > /tmp/r5b && ! cmp -s /tmp/r5a /tmp/r5b'
```
- **Expected observation:** deterministic divergence from the default run
  (θ enters the rotation table; `construct_rope_config` contract at
  `rope.fab:119-121`).
- **Broken:** identical output (θ ignored), or acceptance of θ ≤ 0 /
  non-finite (the constructor's fail-closed domain is
  `InvalidConfig "rope frequency base must be positive"`).

## R6 — Prefill batch: `max_prompt` admission bound

- **Knob setting:** default (model context limit) vs `--max-prompt 1`
- **Runnable when:** OSD-1 landed
- **Command (bound live and observable both ways):**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M 2>&1 | grep -E "^ids=30 2( |$)" && ! $B live --model $M --max-prompt 1 2>&1 | grep -qE "^ids=30 2( |$)"'
```
- **Expected observation:** the frozen 9-token prompt generates under the
  default bound; with `--max-prompt 1` the same run rejects with
  `"prompt length exceeds max_prompt"` (`generation/dense.fab:235` via
  `construct_generation`'s domain, `config.fab:149-150`) — 400 on the serve
  path (`classify_generate_error` maps the cause, `src/main.fab:805-810`).
  The **head state is the inverse of the first half**: today's pin rejects
  the frozen prompt everywhere (serve warm-up fails → 503; live panics) —
  which is exactly what OSD-1 removes.
- **Broken, not merely unused:** a 9-token prompt generating *despite*
  `--max-prompt 1` (admission decorative), or a prompt longer than
  `--context` being accepted.

## R7 — Decode batch / acceleration: context_lookup equivalence

- **Knob setting:** `--acceleration context_lookup --accel-block 4` vs
  disabled (repeat at `--accel-block 1` and `8`)
- **Runnable when:** OSD-5 landed
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; P="The quick brown fox jumps over the lazy dog"; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "$P" --max-tokens 8 2>&1 | grep "^ids=" > /tmp/r7a && for N in 1 4 8; do $B live --model $M --prompt "$P" --max-tokens 8 --acceleration context_lookup --accel-block $N 2>&1 | grep "^ids=" > /tmp/r7b && cmp -s /tmp/r7a /tmp/r7b || exit 1; done'
```
- **Expected observation:** token-identical output to the disabled baseline
  at every block width. The context_lookup path proposes candidates
  (`lookup_candidates`, `generation/dense.fab:121-159`), verifies them as one
  multi-row `decode_block` (`gradus/src/model/dense.fab:693`), and commits
  only the accepted prefix (`commit_dense_block`, `generation/dense.fab:177-198`)
  — divergence from the scalar loop would be a correctness defect in the
  block seam, and that equivalence IS the test of the multi-row batch path.
- **Broken:** any divergence, panic, or silent fallback loop that never
  exercises `decode_block` (observable as identical output *and* unchanged
  run shape — the seat should confirm the code path is reached, not just the
  tokens match).

## R8 — Decode batch / acceleration: greedy-only admission guard

- **Knob setting:** `--acceleration context_lookup` + body
  `"temperature": 0.7`
- **Runnable when:** OSD-5 landed
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B serve --model $M --port 18212 --acceleration context_lookup > /tmp/r8.log 2>&1 & SPID=$!; for i in $(seq 1 60); do grep -qE "generation ready|failed" /tmp/r8.log && break; sleep 5; done; curl -sS -X POST http://127.0.0.1:18212/generate -H "content-type: application/json" --data "{\"prompt\":\"The quick brown fox jumps over the lazy dog\",\"max_tokens\":4,\"temperature\":0.7}" | grep "sampled acceleration is not supported"; RC=$?; kill $SPID 2>/dev/null; exit $RC'
```
- **Expected observation:** HTTP 400 with the typed cause
  `"sampled acceleration is not supported"`
  (`generation/dense.fab:240-243`; `speculative.admit_greedy` carries the
  same law, `gradus/src/speculative.fab:152-158`).
- **Broken:** a 200 (guard bypassed — sampled results under a
  verify-equivalence path would be silently wrong), or an untyped 500.

## R9 — One-shot driver end to end: arbitrary prompt in, decoded result out

- **Knob setting:** defaults only — this is the operator's core ask
- **Runnable when:** OSD-0 + OSD-1 + OSD-2 landed (encode/decode reachability
  needs `fd205b79` on the serve side; live side is OSD-2)
- **Command:**
```bash
bash -ec 'FABER=/Users/ianzepp/work/faberlang/radix/target/debug/faber; M=/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf; B=./target/debug/inferentia; $FABER build . && $B live --model $M --prompt "hello world" --max-tokens 8 2>&1 | tee /tmp/r9.log | grep -E "^text=..+" && grep -E "^ids=..+" /tmp/r9.log'
```
- **Expected observation:** `ids=` carries the tokenizer's encoding of
  "hello world" (≥2 ids — itself proof the admission bound admits real
  prompts), and `text=` is a decoded string that is **not** a space-joined
  integer list (the placeholder `tokens_text` shape, `src/main.fab:743-751`,
  is gone).
- **Broken:** the placeholder shape, an empty `text=`, or a 400/panic on a
  two-token prompt.

## Surfaces deliberately WITHOUT recipes (construction-only in Gradus)

No knob exists and none is added, because the engine ignores these values at
execution — a recipe would be unfalsifiable theater (goal gap ledger):
`v_layout` transposed/straight; `attention_classic/flash`; `sharing_single/
gqa`; `sliding_window`/`compressed_hca`/`indexer` structures and the SWA
kinds; `profile_cuda` (rejected at construction). When Gradus gains execution
paths for any of these, add the recipe then — with the same
broken-vs-unused discriminator.
