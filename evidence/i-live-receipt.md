# I-live receipt — first inferentia run on the gradus provider

**Handle**: `22b52793`  
**Packet**: `worktrees/hand-72`  
**Date**: 2026-08-18  
**Verdict**: **FAIL** vs the U5 16-token golden (`token_match_count=1`).  
G2 `generate_dense` EOG-stop oracle `[30, 2]` matches exactly.

## Existence check (memo 06c99530)

Read-only gradus @ `0711a63d57f2124e1de79dd3a8d3209b42156de6`:

| Symbol | Path | Present |
| --- | --- | --- |
| `generate_dense` | `gradus/src/generation.fab:768` | yes |
| `tokenizator.build` | `gradus/src/tokenizer.fab:929` | yes |
| `tokenizator.build_tables` | `gradus/src/tokenizer.fab:991` | yes |
| `tokenizator.tokenize` | `gradus/src/tokenizer.fab:1793` | yes |

U5 golden available in `docs/factory/inferentia/i1-validation-u5.md`.

## Command

```text
cwd: /Users/ianzepp/work/faberlang/worktrees/hand-72/inferentia/evidence/live-run

FABER_SUPPORT_PATH_OVERRIDE=/Users/ianzepp/work/faberlang \
  /Users/ianzepp/work/faberlang/radix/target/debug/faber check \
  /Users/ianzepp/work/faberlang/worktrees/hand-72/inferentia
# → ok

FABER_SUPPORT_PATH_OVERRIDE=/Users/ianzepp/work/faberlang \
  /Users/ianzepp/work/faberlang/radix/target/debug/faber check \
  /Users/ianzepp/work/faberlang/worktrees/hand-72/inferentia/evidence/live-run
# → ok

FABER_SUPPORT_PATH_OVERRIDE=/Users/ianzepp/work/faberlang \
  /Users/ianzepp/work/faberlang/radix/target/debug/faber build \
  /Users/ianzepp/work/faberlang/worktrees/hand-72/inferentia/evidence/live-run
# rustc E0382 on unused sibling tokenizator.build_tables (token moved into
# per_id then reused for vocabulum). One-line clone applied in the emitted
# crate only (not committed). Then:
cd target/faber && cargo build --offline

./target/faber/target/debug/inferentia-live-run \
  /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf \
  1787040 \
  2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2
```

Wall clock ~22 minutes (32-layer materialize + debug-rust `generate_dense`). Exit 0.

## Model identity

| Fact | Value |
| --- | --- |
| file | `/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf` |
| bytes | `270590880` |
| sha256 | `2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2` |
| data offset | `1787040` |
| admit surface | `gradus:model/gguf_manifest.inspect` + pinned digest/length |
| tokenizer | `gradus:tokenizer.build` → vocab `49152` |
| prompt (G3 `tokenize`) | `[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]` (P10 exact) |
| generate | `gradus:generation.generate_dense` `max_tokens=16` greedy seed=1 |

## Tokens

```text
observed=[30, 2]
golden=[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]
observed.n=2
token_match_count=1
first_divergence=index 1: observed 2 vs golden 198
eog_stop=true
g2_eog_oracle=[30, 2]
g1_unrestrained=[30, 2, 198]
LIVE: FAIL
```

First greedy token `30` matches GATE 13 / GI2 / U5. Token `2` is SmolLM2 EOS; `generate_dense` emits it and halts (`est_eog` set `{0, 2}`). The U5 16-token golden is the llama.cpp / old `model:generate` `ignore_eos` prefix, not the G2 EOG-stop surface.

## Application wire

`inferentia live --model <PATH>` in `src/main.fab` composes the same admit + G3 tables + `generate_dense` path. `faber check` on the product package is green. Product `faber build` is red on pre-existing rustc emit defects (`gguf.admit` references `capsula.schema_versio` out of scope; host-call `String` errors inside `⇥ GgufError` / `do`/`catch`; `build_tables` move). Those are compiler/emit, not missing routes. The live proof therefore ran from `evidence/live-run` (same generate-smollm2 weight path + G3 `build`/`tokenize`).
