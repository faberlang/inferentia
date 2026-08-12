#!/usr/bin/env python3
# =============================================================================
# fixtures.py — I1 U7 admission-failure matrix fixture prep
# =============================================================================
#
# Prepares five same-size local copies of the pinned SmolLM2 row, each patched
# to drive exactly one typed faber-runtime AdmissionError family:
#
#   malformed        GGUF magic overwritten ("GGUF" -> 0xdeadbeef)
#                    -> InvalidMagic: 'invalid GGUF magic: expected "GGUF", ...'
#   wrong-arch       general.architecture value "llama" -> "qwen2" (same length)
#                    -> ArchitectureMismatch: 'architecture "qwen2" != pinned "llama"'
#   wrong-quant      last tensor (output_norm.weight) ggml_type F32 -> Q5_0
#                    -> PerTypeTensorCountMismatch: 'F32 tensor count 64 != expected 65'
#   digest-mismatch  one tensor-data byte flipped at the data region start
#                    -> Sha256Mismatch: 'SHA-256 mismatch: expected 2fa3f013...'
#   unknown-key      last metadata key renamed to a same-length unknown key
#                    -> UnknownMetadataKey: 'unknown metadata key "...z..."'
#
# The copies are byte-identical to the pinned row except for the single patch,
# so each fixture passes every earlier admission check and fails at exactly the
# named cause (fail-closed ordering: magic -> version -> counts -> keys ->
# values -> tensor table -> data bounds -> per-type aggregates -> file size ->
# whole-file SHA-256).
#
# Structural sanity is enforced before any patch: the pinned row must present
# the contracted header facts (magic, version 3, 290 tensors, 37 KVs, the
# "llama" architecture value, and the F32 output_norm.weight last tensor).
# If the row ever changes, prep fails loudly instead of producing a silently
# mis-targeted matrix.
#
# The fixture files themselves (270 MB copies) are NEVER committed; they live
# in a caller-supplied tmpdir and are consumed by run.sh.
#
# Usage: python3 fixtures.py <pinned-model> <outdir>
# Writes <outdir>/*.gguf and <outdir>/manifest.tsv
#   manifest line: <path>\t<expected-cause-substring>
# =============================================================================

import hashlib
import os
import struct
import sys

PINNED_SHA256_HEX = "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"

EXPECTED_TENSOR_COUNT = 290
EXPECTED_KV_COUNT = 37
GGUF_ALIGNMENT = 32

# ggml_type ids used by the pinned row (llama.cpp enum).
GGML_F32 = 0
GGML_Q5_0 = 6

# Value-tag byte widths for GGUF scalar types (tags not listed are u64/u32
# handled explicitly; arrays handled specially).
SCALAR_BYTES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def skip_value(data, off, tag):
    """Advance past one GGUF metadata value at `off`, return the next offset."""
    if tag == 9:  # array: u32 element tag + u64 count + elements
        elem_tag = struct.unpack_from("<I", data, off)[0]
        off += 4
        count = struct.unpack_from("<Q", data, off)[0]
        off += 8
        if elem_tag == 8:  # array<STRING>
            for _ in range(count):
                ln = struct.unpack_from("<Q", data, off)[0]
                off += 8 + ln
        elif elem_tag == 5:  # array<I32>
            off += 4 * count
        else:
            off += SCALAR_BYTES.get(elem_tag, 4) * count
        return off
    if tag == 8:  # string: u64 len + bytes
        ln = struct.unpack_from("<Q", data, off)[0]
        return off + 8 + ln
    return off + SCALAR_BYTES.get(tag, 4)


def parse_header(data):
    """Parse the GGUF header; return (arch_value_off, last_kv_key_off,
    last_tensor_gtype_off, data_offset, tensor_table_start)."""
    magic = data[0:4]
    version = struct.unpack_from("<I", data, 4)[0]
    tensor_count = struct.unpack_from("<Q", data, 8)[0]
    kv_count = struct.unpack_from("<Q", data, 16)[0]

    if magic != b"GGUF":
        sys.exit(f"fixture prep aborted: pinned model magic {magic!r} != b'GGUF'")
    if version != 3:
        sys.exit(f"fixture prep aborted: pinned model version {version} != 3")
    if tensor_count != EXPECTED_TENSOR_COUNT:
        sys.exit(
            f"fixture prep aborted: tensor_count {tensor_count} != {EXPECTED_TENSOR_COUNT}"
        )
    if kv_count != EXPECTED_KV_COUNT:
        sys.exit(f"fixture prep aborted: metadata_kv_count {kv_count} != {EXPECTED_KV_COUNT}")

    off = 24
    arch_value_off = None
    last_kv_key_off = None
    for _ in range(kv_count):
        key_off = off
        klen = struct.unpack_from("<Q", data, off)[0]
        off += 8
        key = data[off : off + klen].decode("utf-8")
        off += klen
        tag = struct.unpack_from("<I", data, off)[0]
        off += 4
        if key == "general.architecture":
            vlen = struct.unpack_from("<Q", data, off)[0]
            off += 8
            arch_value_off = off
            if data[off : off + vlen] != b"llama":
                sys.exit(
                    "fixture prep aborted: general.architecture is not 'llama' "
                    "(pinned row changed; re-baseline the matrix)"
                )
            off += vlen
        else:
            off = skip_value(data, off, tag)
        last_kv_key_off = key_off

    tensor_table_start = off
    last_tensor_gtype_off = None
    last_tensor_name = None
    for _ in range(tensor_count):
        nlen = struct.unpack_from("<Q", data, off)[0]
        off += 8
        name = data[off : off + nlen].decode("utf-8")
        off += nlen
        ndims = struct.unpack_from("<I", data, off)[0]
        off += 4
        for _ in range(ndims):  # dims are u64 in GGUF
            off += 8
        gtype_off = off
        off += 4  # ggml_type
        off += 8  # offset_in_data
        last_tensor_gtype_off = gtype_off
        last_tensor_name = name

    if last_tensor_name != "output_norm.weight":
        sys.exit(
            f"fixture prep aborted: last tensor {last_tensor_name!r} != "
            "'output_norm.weight' (pinned row changed; re-baseline the matrix)"
        )
    gtype = struct.unpack_from("<I", data, last_tensor_gtype_off)[0]
    if gtype != GGML_F32:
        sys.exit(
            "fixture prep aborted: last tensor ggml_type is not F32 "
            "(pinned row changed; re-baseline the matrix)"
        )

    data_offset = (off + GGUF_ALIGNMENT - 1) & ~(GGUF_ALIGNMENT - 1)
    return arch_value_off, last_kv_key_off, last_tensor_gtype_off, data_offset, tensor_table_start


def patch_copy(data, out_path, patches):
    """Write a byte-identical copy of the pinned row with the given patches
    (each patch is a (offset, bytes) pair applied in order)."""
    buf = bytearray(data)
    for offset, raw in patches:
        buf[offset : offset + len(raw)] = raw
    with open(out_path, "wb") as f:
        f.write(buf)


def main(argv):
    if len(argv) != 3:
        sys.exit("usage: python3 fixtures.py <pinned-model> <outdir>")
    model_path, outdir = argv[1], argv[2]

    with open(model_path, "rb") as f:
        data = f.read()

    digest = hashlib.sha256(data).hexdigest()
    if digest != PINNED_SHA256_HEX:
        sys.exit(
            f"fixture prep aborted: pinned model sha256 {digest} != {PINNED_SHA256_HEX} "
            "(identity gate; a different row cannot be matrixed against the U7 offsets)"
        )

    arch_off, last_key_off, last_tensor_gtype_off, data_offset, tensor_start = parse_header(data)
    os.makedirs(outdir, exist_ok=True)

    last_key_len = struct.unpack_from("<Q", data, last_key_off)[0]
    last_key_bytes = data[last_key_off + 8 : last_key_off + 8 + last_key_len]

    fixtures = [
        (
            "malformed",
            [(0, b"\xde\xad\xbe\xef")],
            "invalid GGUF magic",
        ),
        (
            "wrong-arch",
            [(arch_off, b"qwen2")],
            'architecture "qwen2"',
        ),
        (
            "wrong-quant",
            [(last_tensor_gtype_off, struct.pack("<I", GGML_Q5_0))],
            "F32 tensor count 64 != expected 65",
        ),
        (
            "digest-mismatch",
            [(data_offset, bytes([data[data_offset] ^ 0xFF]))],
            "SHA-256 mismatch",
        ),
        (
            "unknown-key",
            [(last_key_off + 8, b"z" * last_key_len)],
            "unknown metadata key",
        ),
    ]

    manifest_lines = []
    for name, patches, expected in fixtures:
        out_path = os.path.join(outdir, f"{name}.gguf")
        patch_copy(data, out_path, patches)
        manifest_lines.append(f"{out_path}\t{expected}")

    manifest_path = os.path.join(outdir, "manifest.tsv")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines) + "\n")

    print(
        f"fixtures prepared in {outdir} "
        f"(arch value @ {arch_off}, last kv key @ {last_key_off} "
        f"({last_key_bytes.decode('utf-8')}), last tensor gtype @ "
        f"{last_tensor_gtype_off}, data region @ {data_offset})"
    )
    for name, _, expected in fixtures:
        print(f"  {name:16s} -> {expected}")


if __name__ == "__main__":
    main(sys.argv)
