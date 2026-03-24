#!/usr/bin/env python3
"""Merge WAN 2.2 shard directories into single safetensors files.

Uses memory-mapped streaming so peak RAM = largest single tensor (~600MB),
not the full model size (~54GB per variant).

Usage:
    python3 scripts/merge_wan_shards.py

Outputs (in models/diffusion_models/):
    wan2.2-i2v-14B-high.safetensors
    wan2.2-i2v-14B-low.safetensors

After verifying the outputs load correctly, delete the shard directories:
    rm -rf models/diffusion_models/wan2.2-i2v/
"""

import json
import struct
import glob
import os
import sys
import time
from safetensors import safe_open

DTYPE_SIZES = {
    "F64": 8, "F32": 4, "F16": 2, "BF16": 2,
    "F8_E4M3": 1, "F8_E5M2": 1,
    "I64": 8, "I32": 4, "I16": 2, "I8": 1,
    "U64": 8, "U32": 4, "U16": 2, "U8": 1,
    "BOOL": 1,
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIFFUSION_MODELS = os.path.join(REPO_ROOT, "models", "diffusion_models")

VARIANTS = [
    ("wan2.2-i2v/high_noise", "wan2.2-i2v-14B-high.safetensors"),
    ("wan2.2-i2v/low_noise",  "wan2.2-i2v-14B-low.safetensors"),
]


def tensor_nbytes(dtype, shape):
    n = DTYPE_SIZES[dtype]
    for s in shape:
        n *= s
    return n


def merge(shard_dir, output_path):
    shards = sorted(glob.glob(os.path.join(shard_dir, "diffusion_pytorch_model-*-of-*.safetensors")))
    if not shards:
        print(f"  No shards found in {shard_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(shards)} shards → {output_path}")

    # Pass 1: collect metadata (fast, header-only reads via mmap)
    shard_keys = []  # [(shard_path, [(key, dtype, shape), ...])]
    for shard in shards:
        keys = []
        with safe_open(shard, framework="numpy") as f:
            for key in f.keys():
                sl = f.get_slice(key)
                keys.append((key, sl.get_dtype(), list(sl.get_shape())))
        shard_keys.append((shard, keys))

    # Compute output layout
    offset = 0
    header = {}
    for _, keys in shard_keys:
        for key, dtype, shape in keys:
            n = tensor_nbytes(dtype, shape)
            header[key] = {"dtype": dtype, "shape": shape, "data_offsets": [offset, offset + n]}
            offset += n + (8 - n % 8) % 8  # 8-byte alignment

    header_json = json.dumps(header, separators=(",", ":")).encode()

    total_bytes = offset
    written = 0
    t0 = time.time()

    # Pass 2: stream tensor data shard by shard
    with open(output_path, "wb") as out:
        out.write(struct.pack("<Q", len(header_json)))
        out.write(header_json)

        for shard_idx, (shard, keys) in enumerate(shard_keys):
            print(f"    [{shard_idx + 1}/{len(shards)}] {os.path.basename(shard)}")
            with safe_open(shard, framework="numpy") as f:
                for key, dtype, shape in keys:
                    data = f.get_tensor(key).tobytes()
                    out.write(data)
                    pad = (8 - len(data) % 8) % 8
                    if pad:
                        out.write(b"\x00" * pad)
                    written += len(data) + pad

            elapsed = time.time() - t0
            pct = written / (total_bytes or 1) * 100
            speed_mb = written / elapsed / 1024 / 1024 if elapsed > 0 else 0
            print(f"    {pct:.1f}% done  {speed_mb:.0f} MB/s")

    elapsed = time.time() - t0
    size_gb = os.path.getsize(output_path) / 1024 ** 3
    print(f"  Done: {size_gb:.1f}GB in {elapsed:.0f}s")


def main():
    for shard_subdir, out_name in VARIANTS:
        shard_dir = os.path.join(DIFFUSION_MODELS, shard_subdir)
        output_path = os.path.join(DIFFUSION_MODELS, out_name)

        if not os.path.isdir(shard_dir):
            print(f"Skipping {shard_subdir} (directory not found)")
            continue

        if os.path.exists(output_path):
            print(f"Skipping {out_name} (already exists)")
            continue

        print(f"\nMerging: {shard_subdir}")
        merge(shard_dir, output_path)

    print("\nAll done. Verify the merged files load correctly, then delete shard dirs:")
    print("  rm -rf models/diffusion_models/wan2.2-i2v/")


if __name__ == "__main__":
    main()
