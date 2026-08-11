# I1-U5 Validation Log — Oracle match (tokenization + greedy)

**Unit**: U5 — Oracle match (i1-delivery §6, row U5; slice-1 final gate)
**Hand**: hand-7 (task `a86f58f8`)
**Date**: 2026-08-11
**Repo**: inferentia @ `main` (working tree clean before this unit)
**Documented tolerance**: exact — GI2 §4.1 top-1 non-EOG surface (i1-delivery
row U5, campaign gate "Tokenization + deterministic selection match oracle
within documented tolerance | U5 (exact, GI2 §4.1)").

## Environment (re-pinned at execution time)

- faber: `~/.local/bin/faber` → `faber 1.6.0` (REBUILT binary per task note)
- llama.cpp: 10150 `dee2a846b` (`/opt/homebrew/bin/llama-tokenize`,
  `/opt/homebrew/bin/llama-server`)
- Model: `/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf`
  - size: 270,590,880 bytes
  - SHA-256: `2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2`
- Fixture (i1-discovery §6.1): prompt text
  `The quick brown fox jumps over the lazy dog`
- Pinned P10 prompt tokens: `[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]`
- Gate authority: `faber-runtime/testdata/gi2-4-greedy-record/record.json`
  (SHA-256 of record `ed3169db…`; generated 256 tokens, `all_agree: true`,
  `first_divergence: null`)

## Comparison 1 — Tokenization: `llama-tokenize --ids` P10 vs pinned P10

Command (fresh run, discovery §6.2 oracle form):

```sh
/opt/homebrew/bin/llama-tokenize -m \
  /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf \
  -p "The quick brown fox jumps over the lazy dog" --ids
```

Observed output:

```
[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]
```

| Surface | Array |
| --- | --- |
| `llama-tokenize --ids` P10 (fresh) | `[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]` |
| Pinned P10 (`pinned_prompt()`, engine input) | `[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]` |
| record.json `prompt_tokens` (gate authority) | `[504, 2365, 6354, 16438, 27003, 690, 260, 23790, 2767]` |

**MATCH**: all three surfaces identical.

## Comparison 2 — Greedy: fresh token-array oracle run vs record.json

Fresh oracle server (discovery §6.2 pinned comparator launch):

```sh
/opt/homebrew/bin/llama-server --host 127.0.0.1 --port 8765 \
  --model /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf \
  --parallel 1 --batch-size 1024 --ubatch-size 256 --ctx-size 8192 \
  --cache-type-k f16 --cache-type-v f16 --flash-attn on \
  --n-gpu-layers 99 --threads 6 --threads-batch 6 \
  --jinja --mmap --reasoning off --reasoning-budget 0
```

Health: `{"status":"ok"}` before the completion post.

Pinned token-array `/completion` invocation (discovery §6.2):

```sh
curl -s http://127.0.0.1:8765/completion -H 'Content-Type: application/json' \
  -d '{"prompt":[504,2365,6354,16438,27003,690,260,23790,2767],"n_predict":16,"temperature":0,"seed":42,"top_k":40,"top_p":0.95,"min_p":0.05,"typical_p":1.0,"repeat_penalty":1.0,"ignore_eos":true,"stop":[],"stream":false,"cache_prompt":false,"n_probs":40}'
```

Observed response facts: `tokens_predicted: 16`, `tokens_evaluated: 9`
(prompt), `stop_type: "limit"`, `temperature: 0.0`, `ignore_eos` applied.

Trace head (`completion_probabilities[i].id`, top-1 per position):

```
[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]
```

| Surface | Array |
| --- | --- |
| Fresh `/completion` oracle trace (top-1, 16 tokens) | `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]` |
| record.json `generated_tokens[0..16]` (gate authority) | `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]` |

**MATCH**: identical.

## Comparison 3 — Greedy: engine probe (`generate-gate`) vs record.json

Probe: `tests/generate-gate` (compiled release binary), drives the real
`model:generate` route (BD-2 execution bridge) with the frozen fixture config:
`contextus 8192, maxima_verborum 16, semen 1, temperatura 0.0, top_k 0,
top_p 1.0, min_p 0.0, poena_repetitionis 1.0` and the pinned P10 prompt.

Command:

```sh
cd tests/generate-gate && faber build . --release && ./target/release/generate-gate
```

Observed stdout (relevant lines):

```
U5 P10 (pinned prompt tokens): [504,2365,6354,16438,27003,690,260,23790,2767]
PASS U5 tokenization: P10 == record.json prompt_tokens
U5 record.json prompt_tokens: [504,2365,6354,16438,27003,690,260,23790,2767]
U5 record.json generated_tokens[0..16]: [30,198,198,504,808,6330,314,253,2232,4814,282,1027,28,979,260,1796]
request1: 16 tokens
request1 tokens: [30,198,198,504,808,6330,314,253,2232,4814,282,1027,28,979,260,1796]
PASS request1: ≥16 tokens, no EOG id from {0,2} admitted
PASS max_tokens budget: 16 == record.json prefix
GENERATE GATE ALL PASS
```

Observed stderr (load-once evidence):

```
generate-gate: model load 1 (resident — loaded exactly once)
```

| Surface | Array |
| --- | --- |
| Engine probe `request1 tokens` (16 generated, exact) | `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]` |
| record.json `generated_tokens[0..16]` (gate authority) | `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]` |
| Fresh `/completion` oracle trace (comparison 2) | `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979, 260, 1796]` |

**MATCH**: exact direct comparison in-probe (`expect_sequence`,
`PASS max_tokens budget: 16 == record.json prefix`), exit 0.

## Plain match statement

- Tokenization: `llama-tokenize --ids` reproduces the pinned P10 and
  `record.json prompt_tokens` exactly (9/9 ids equal).
- Greedy (fresh oracle): the fresh pinned `/completion` token-array run
  reproduces `record.json generated_tokens[0..16]` exactly (16/16 ids equal).
- Greedy (engine probe): the compiled `generate-gate` probe reproduces
  `record.json generated_tokens[0..16]` exactly (16/16 ids equal, in-probe
  direct comparison), with the resident-model load-once stderr evidence.
- No EOG id from `{0,2}` appears in the 16-token window (top-1 non-EOG
  surface contract), matching the record's first-divergence-null surface.

## Unit-level gates (re-run for this unit)

- `faber check .` → `ok: .`
- `faber test .` → `test result: ok. 40 passed; 0 failed; 0 skipped`
- `git diff --check` → clean
- Probe package `faber check .` → `ok: .`; probe exit 0

**Result: U5 done-when met — tokenization + greedy oracle match, exact.**
