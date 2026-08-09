# I1 — Entry Evidence (discovery record)

**Campaign**: Inferentia (faberlang/inferentia)
**Stage**: I1 — Small GGUF vertical slice
**Author**: planner-1 (task `196fb361`, goal-forge + discovery)
**Date**: 2026-08-09
**Status**: frozen — evidence captured live; authority for `i1-delivery.md`

Every fact below was re-verified against the live machine and live sources on
2026-08-09, not copied from memory or prior docs. Read-only discovery only:
no artifacts were downloaded, copied, or modified.

---

## 1. Model artifacts — present on this machine

All three I1 target rows are **present** at `/Users/ianzepp/ai/models/`
(verified `ls -la`, Aug 5 2026; SHA-256 computed 2026-08-09 via `shasum -a 256`).

| Row | Absolute path | Bytes | SHA-256 (whole file) |
| --- | --- | --- | --- |
| SmolLM2-360M-Instruct-Q4_K_M | `/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf` | 270,590,880 | `2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2` |
| Qwen2.5-0.5B-Instruct-Q4_K_M | `/Users/ianzepp/ai/models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf` | 397,808,192 | `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653` |
| Qwen2.5-1.5B-Instruct-Q4_K_M | `/Users/ianzepp/ai/models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf` | 986,048,768 | `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370` |

The SmolLM2 hash and size **cross-validate** against faber-runtime
`src/model_format.rs` constants (`PINNED_SHA256_HEX`,
`PINNED_FILE_SIZE = 270_590_880`) and the GI2 greedy-record manifest.

## 2. GGUF metadata (parsed live, 2026-08-09)

Read-only parse of the GGUF header (LE binary walk); data offsets
cross-validated against `/opt/homebrew/bin/llama-gguf r` (version 10150,
`dee2a846b`) — identical values.

### 2.1 SmolLM2-360M-Instruct-Q4_K_M

| Field | Value |
| --- | --- |
| GGUF version | 3 |
| KV count / tensor count | 37 / 290 |
| Metadata end / data offset | 1,769,783 / **1,787,040** (32-aligned) |
| architecture | `llama` |
| block_count / context_length | 32 / 8192 |
| embedding_length / ffn_length | 960 / 2560 |
| head_count / head_count_kv | 15 / 5 |
| rope.freq_base / rope.dimension_count | 100000.0 / 64 |
| layer_norm_rms_epsilon | ~1e-5 |
| vocab_size | 49152 |
| general.file_type | 15 (`MOSTLY_Q4_K_M`) |
| general.quantization_version | 2 |
| tokenizer.ggml.model / pre | `gpt2` / `smollm` |
| special ids (bos/eos/pad/unk) | 1 / 2 / 2 / 0 |
| add_bos_token / add_space_prefix | false / false |
| tokenizer.chat_template | present (368 chars) |
| Tensor type distribution | F32 65 · Q5_0 176 · Q6_K 16 · Q8_0 17 · Q4_K 16 |
| First tensor | `token_embd.weight` [960, 49152], Q8_0 |

Facts match gradus `model/gguf.fab` pinned constants and faber-runtime
`model_format.rs` (`EXPECTED_KV_COUNT 37`, `EXPECTED_TENSOR_COUNT 290`,
GGUF version 3) exactly.

### 2.2 Qwen2.5-0.5B-Instruct-Q4_K_M

| Field | Value |
| --- | --- |
| GGUF version | 3 |
| KV count / tensor count | 38 / 290 |
| Metadata end / data offset | 5,931,975 / **5,948,480** |
| architecture | `qwen2` |
| block_count / context_length | 24 / 32768 |
| embedding_length / ffn_length | 896 / 4864 |
| head_count / head_count_kv | 14 / 2 |
| rope.freq_base | 1000000.0 |
| layer_norm_rms_epsilon | ~1e-6 |
| vocab_size | 151936 |
| general.file_type / quantization_version | 15 / 2 |
| tokenizer.ggml.model / pre | `gpt2` / `qwen2` |
| special ids (bos/eos/pad) | 151643 / 151645 / 151643 |
| add_bos_token | false |
| tokenizer.chat_template | present (2507 chars) |
| Tokenizer arrays | tokens 151,936 · merges 151,387 · token_type 151,936 (i32, all 1) |
| Tensor type distribution | F32 121 · Q5_0 132 · Q6_K 12 · Q8_0 13 · Q4_K 12 |
| First tensor | `token_embd.weight` [896, 151936], Q8_0 |

### 2.3 Qwen2.5-1.5B-Instruct-Q4_K_M

| Field | Value |
| --- | --- |
| GGUF version | 3 |
| KV count / tensor count | 38 / 338 |
| Metadata end / data offset | 5,931,975 / **5,951,232** |
| architecture | `qwen2` |
| block_count / context_length | 28 / 32768 |
| embedding_length / ffn_length | 1536 / 8960 |
| head_count / head_count_kv | 12 / 2 |
| rope.freq_base | 1000000.0 |
| layer_norm_rms_epsilon | ~1e-6 |
| vocab_size | 151936 |
| general.file_type / quantization_version | 15 / 2 |
| tokenizer.ggml.model / pre | `gpt2` / `qwen2` |
| special ids (bos/eos/pad) | 151643 / 151645 / 151643 |
| add_bos_token | false |
| tokenizer.chat_template | present (2507 chars) |
| Tokenizer arrays | tokens 151,936 · merges 151,387 · token_type 151,936 |
| Tensor type distribution | F32 141 · Q6_K 29 · Q4_K 168 |
| First tensor | `token_embd.weight` [1536, 151936], Q6_K |

### 2.4 Batch-boundary conclusion (evidence)

- The **two Qwen rows share** architecture `qwen2`, tokenizer (`gpt2` / `qwen2`
  pre, identical special ids and vocab), quantization (`file_type 15`,
  `quantization_version 2`, quant vocabulary within {F32, Q4_K, Q5_0, Q6_K,
  Q8_0}), and execution path (same engine family: RMSNorm · RoPE · GQA ·
  SwiGLU · dense, untied output head). They differ only in row parameters
  (24/28 layers, 896/1536 embedding, 14/12 heads) and per-type tensor counts.
  → **One batch**, no split boundary between them.
- **SmolLM2 vs Qwen crosses a real boundary**: architecture id `llama` vs
  `qwen2`, tokenizer pre `smollm` vs `qwen2`, vocab 49,152 vs 151,936, context
  8192 vs 32768, tied vs untied output head, rope freq_base 1e5 vs 1e6,
  eps 1e-5 vs 1e-6. The pinned SmolLM2 admission contract (gradus
  `model/gguf.fab`; faber-runtime `model_format.rs`) **rejects** the Qwen rows
  today. → **Split**: SmolLM2 is the single-row first slice; the Qwen pair is a
  batch that rejoins after the SmolLM2 row passes.

## 3. Gradus surfaces (live, `gradus/src/`, HEAD `24feb82`)

Public imports (leaf modules, `importa ex "gradus:…"`):

| Module | Public surface (verified) | Notes |
| --- | --- | --- |
| `gradus:model/gguf` | `admit(bytes, digestio, digestio_vocabuli, expectatum_kv, expectatum_tensorum, expectatum_elementa, expectatum_f32, expectatum_q4k, expectatum_q5, expectatum_q6, expectatum_q8, semita) → Capsula ⇥ GgufError`; `causa` | **Pinned to the SmolLM2 row only** (37 keys, 290 tensors, arch llama, 32 layers, context 8192, vocab 49152, embedding 960, tokenizer gpt2/smollm, EOG {0,2}). Any unknown key or value mismatch fails closed. |
| `gradus:model/capsule` | `capsula.structa(…)`; `Capsula` / `Identitas` accessors; `verifica`; schema `capsule-schema-1.0.0` | Typed identity handoff; whole-file SHA-256 + vocab digest are **host-computed and passed in** (no crypto in the language). |
| `gradus:model/dequant` | `elementa_glomoris(typo)`, `octeti_glomoris(typo)`, `dequantizas_glomulus(typo, blocci)`, `dequantizas_ordo(typo, octeti)`; `DequantError` | Block-layout + per-block/row dequant for {F32, Q4_K, Q5_0, Q6_K, Q8_0}. |
| `gradus:tokenizer` | `structa`, `verifica`, `est_eog`, `proba_ida`, `verifica_proba`, `pinnata_proba` (P1–P11 + 4 workloads), `clavis_tokenizatoris`, `serializa_identitas`/`deserializa_identitas` | Identity + probe-parity contract, **not a runtime encoder**. Pinned probes P1–P11 and workload id lists (9/9/202/2175) embedded as fixtures. |
| `gradus:decode` | `structa_decodere`, `decodere_datum(token_id, positio, decodere) → tensor`, `praefundere(tokens, decodere)`, `sessio_fresh`/`progredere`/`redintegra`, `cancelatum_fresh`/`cancelatum_cancellata`/`observa_cancellationem`, `replica(logita, config, historia, semen, cancelatum)`; `Decodere`, `Pondera`, `Sessio`, `Cancelatum` | Shared transformer-block forward row (mode 2 = causal + RoPE). Reject-policy on context/position; cooperative cancellation. |
| `gradus:cache` | `cache_vacua`, `appende`, `redintegra`, `identitas_cache`, `serializa_identitas`/`deserializa_identitas`; `KVCache`, `IdentitasCache` | Per-session K/V logical state, versioned identity key (MD-A9). |
| `gradus:sampling` | `structa_configura`, `maxima` (greedy), `distributio`, `sors`; `Configura` | Deterministic pipeline: repetition penalty → temperature → top-k → softmax → top-p → min-p → draw (xorshift64 via `gradus:train`). `temperatura ≤ 0` = greedy path. |
| `gradus:generation` | `structa_generatio`, `generatio_defecta`, `configura`, `semen`, `imperia_subsidia` (nine fields), `imperium_admissum`, `serializa_generatio`/`deserializa_generatio`, `cursor_fresh`/`verbum_licet`/`cursor_progredere`/`cursor_redintegra`; `GeneratioConfigura` | **Single authority** for generation config (nine fields: contextus, magna_promptus, maxima_verborum, semen, temperatura, top_k, top_p, min_p, poena_repetitionis). Reject-not-truncate cursor. |
| `gradus:train` | `structa_semen` (seed ≥ 1), `proximus_f32` (xorshift64); `Semen` | Explicit RNG seam. |

**Runtime status (honesty, recorded in every gradus module)**: all Gradus
computation surfaces are **compile-validated**; executed value identity is
**env-blocked tree-wide** (FMIR stepper / library-import gap — PML4 closeout
recording). Gradus proba proof is compile-level until `faber test` runs
library probas. This is the campaign's biggest reusable-primitive prerequisite
(see BD-1/BD-3 in `i1-delivery.md`).

## 4. Executable engine (faber-runtime, live, HEAD `3e2f8d9`)

The physical engine for the pinned SmolLM2 row exists in **Rust**
(faber-runtime), Rust-tested, deterministic:

| Surface | Verified |
| --- | --- |
| `model_format::admit_pinned(bytes)` / `admit_pinned_file(path) → PinnedAdmission` | Pinned row only: 37 KV, 290 tensors, whole-file SHA-256 `2fa3f013…`, size 270,590,880, GGUF v3, file_type 15, quant v2. 34 admission tests green (GI1). |
| `model_widen::TensorView::build(&PinnedAdmission, &bytes)` | Coverage-gated (`coverage_ok`); per-tensor descriptors + receipts. |
| `cpu_oracle::CpuOracle::build(&view)` → `forward_one(&[i64]) → Vec<f32>` (full-vocab logits) | 32-layer decoder (RMSNorm · RoPE NORM · GQA 15/5 · SwiGLU · dense); tied-head projection. GI2: byte-identical to the reference executor. |
| `ForwardRun` (incremental, per-position K/V) | No numeric change vs full forward. |
| `top1_non_eog(logits, &[0,2])` | Greedy over non-EOG. |
| `greedy_run` record | `testdata/gi2-4-greedy-record/record.json`: 256 greedy tokens from the pinned 9-token prompt, `all_agree: true`, `first_divergence: null`, SHA-256 `ed3169db…`; produced by a release-profile Rust test (~64 s). |
| Golden logits | `testdata/gi2-3-logits-golden/logits-pos0.json` (49,152 logp). |

**Not callable from a Faber application today** — no host-provider or library
binding exposes the engine to compiled Faber code (see BD-2). The tokenizer
runtime was deliberately removed from faber-runtime (PML2 C3, commit
`07f9243`, 2026-08-09): `src/tokenizer/{mod,bpe,pretoken}.rs` were `git rm`'d;
its parity facts are now oracle material for the Gradus port — **there is no
executable text→ids encoder anywhere in the stack today**.

## 5. Norma / Host effects available to a Faber app (live)

### 5.1 HTTP server — available

`norma:http` (norma `src/http.fab`) wraps the hosts `http:*` provider via
`ad 'http:…'`:

| Faber function | Host route | Semantics |
| --- | --- | --- |
| `http.listen(args) → numerus` | `http:listen` | Bind loopback HTTP/1.1 listener `[port, max_body_bytes?]` → handle. Default body cap 1 MiB, max 16 MiB; header cap 64 KiB. |
| `http.accept(handle) → valor` | `http:accept` | Accept **one** request (blocking pull); carrier = {id, method, path, headers, body(octeti)}. |
| `http.respond([request_id, status, headers, body]) → vacuum` | `http:respond` | Write one response; **always** `connection: close`, `content-length` fixed. |
| `http.stop(handle) → vacuum` | `http:stop` | Stop listener, close pending request streams. |

Provider: `hosts/crates/http` (`src/lib.rs`, manifest `http:listen/accept/
respond/stop`). Loopback-only (`127.0.0.1`), **single-threaded pull loop, one
request at a time**, no chunked/streamed responses, no keep-alive.

**Streaming conclusion**: the current provider **cannot stream** (one-shot
response, content-length, connection close). A minimal stream requires a new
host effect — an I2 prerequisite. I1 is deliberately non-streaming.

HTTP client verbs in `norma:http` (`petet`, `mittet`, `ponet`, `delet`,
`mutabit`, `rogabit`) are **deferred `mori` stubs** — not available.

### 5.2 File / clock effects — available

- `norma:solum` → `solum:hauri` (read whole file → octeti), `solum:partem`
  (bounded byte range), `solum:mensura` (file size), `solum:exstat` (exists),
  `solum:scribe`/`solum:funde` (write), etc. — all implemented in the hosts
  `solum` provider (routes verified in `hosts/crates/solum/src/lib.rs`).
- `norma:tempus` → `tempus:nunc`, `tempus:monotonicum` (clock) — implemented.
- Provider auto-selection: the faber package plan derives providers from the
  `ad` route prefix (`http:…` → `http`, `solum:…` → `solum`, …) and generates
  a `main` + `host_register` that registers them with the kernel when the
  package declares native host bootstrap (`[target.rust] host = "native"`).
  Evidence: `faber/src/package/rust_target.rs` + `dispatch.rs`
  (`selected_providers_for_routes`, `load_provider_manifests`).

### 5.3 JSON and TOML — deferred (gaps)

- `norma:json` — `solve` / `pange` / `tempta` are **deferred `mori` stubs**
  ("pending runtime codec dispatch"). No JSON codec exists in the language.
- `norma:toml` — `pange` / `solve` / `tempta` are **deferred `mori` stubs**.
  No TOML parsing exists.

## 6. Frozen prompt fixture + oracle

### 6.1 Frozen request fixture (slice 1 — SmolLM2)

- Prompt text: `The quick brown fox jumps over the lazy dog`
- Pinned prompt tokens: `[504, 2365, 6354, 16438, 27003, 690, 260, 23790,
  2767]` (gradus `tokenizer.fab` `PINNATA_P10`; `evidence/contract-tokenize-
  probes.txt`; GI2 greedy-record `prompt_tokens`).
- Request (deterministic greedy): `{"prompt":"The quick brown fox jumps over
  the lazy dog","max_tokens":16,"temperature":0.0,"top_k":0,"top_p":1.0,
  "min_p":0.0,"repeat_penalty":1.0,"seed":1}`
- Expected generated tokens: `record.json` `generated_tokens[0..16]` =
  `[30, 198, 198, 504, 808, 6330, 314, 253, 2232, 4814, 282, 1027, 28, 979,
  260, 1796]` (temperature 0, EOG {0,2} excluded, all_agree).

### 6.2 Oracle commands (llama.cpp 10150 `dee2a846b`, comparison-only)

```sh
# tokenizer probe parity (P10)
/opt/homebrew/bin/llama-tokenize -m \
  /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf \
  -p "The quick brown fox jumps over the lazy dog"

# greedy generation oracle
/opt/homebrew/bin/llama-cli -m \
  /Users/ianzepp/ai/models/SmolLM2-360M-Instruct-Q4_K_M.gguf \
  -p "The quick brown fox jumps over the lazy dog" -n 16 --temp 0 --seed 1 \
  --no-display-prompt
```

Exact `llama-cli` flag spellings for token-level output (`-j`/`--log-json`,
`--verbose-prompt`) are verified at I1 execution time and recorded in the
validation log; `evidence/contract-tokenize-probes.txt` +
`testdata/gi2-4-greedy-record/record.json` are the committed comparison
authority. Qwen oracle runs are produced fresh at execution time for the
batch gate and recorded in the validation log.

## 7. Pinned facts vs this machine — summary

| Claim | Status |
| --- | --- |
| Three I1 GGUF rows present at `/Users/ianzepp/ai/models/` | ✅ verified (paths/sizes/hashes recorded) |
| SmolLM2 admission contract (arch/quant/tokenizer) matches gradus + faber-runtime pinned constants | ✅ verified (metadata + cross-checked digest) |
| Qwen pair share arch/tokenizer/quant/execution path | ✅ verified → one batch |
| SmolLM2 vs Qwen crosses a real boundary | ✅ verified → split (SmolLM2 slice first) |
| Gradus computation surfaces exist | ✅ verified (APIs listed) |
| Gradus execution (value identity) | ❌ **env-blocked** (FMIR stepper / library-import gap) |
| Tokenizer runtime encoder | ❌ **missing** (removed from faber-runtime; only parity fixtures remain) |
| Execution bridge Faber app → engine | ❌ **missing** (no provider/bindings) |
| HTTP server effect | ✅ available (loopback, one request at a time, no streaming) |
| File read / clock effects | ✅ available |
| JSON / TOML codecs | ❌ **deferred** (Norma `mori` stubs) |
| Frozen fixture + oracle | ✅ frozen (fixture + record.json + llama commands) |
