#!/usr/bin/env bash
# Resilient Qwen-Image-Edit downloader. hf download resumes from the .incomplete
# cache, so we just loop until each file lands. Throwaway helper (gitignored use).
set -u
export PATH="$HOME/.local/bin:$PATH"
# hf_xet hangs on flaky networks (process alive, 0 bytes moving). Force plain
# HTTPS LFS, which is range-resumable and recovers cleanly across drops.
export HF_HUB_DISABLE_XET=1
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_DOWNLOAD_TIMEOUT=30
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE=/tmp/qwendl
MAXTRY=200

pull() {  # repo  repofile  localdir
  local repo="$1" file="$2" dir="$3" n=0
  until hf download "$repo" "$file" --local-dir "$dir" >/dev/null 2>&1; do
    n=$((n+1))
    if [ "$n" -ge "$MAXTRY" ]; then echo "GIVEUP after $n tries: $file"; return 1; fi
    echo "retry $n: $file"
    sleep 8
  done
  echo "OK: $file"
}

echo "=== [1/4] GGUF transformer (16.8 GB) ==="
pull QuantStack/Qwen-Image-Edit-2509-GGUF Qwen-Image-Edit-2509-Q6_K.gguf "$REPO/models/diffusion_models/" || exit 1

echo "=== [2/4] text encoder (~9 GB) ==="
pull Comfy-Org/Qwen-Image_ComfyUI split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors "$STAGE" || exit 1

echo "=== [3/4] vae ==="
pull Comfy-Org/Qwen-Image_ComfyUI split_files/vae/qwen_image_vae.safetensors "$STAGE" || exit 1

echo "=== [4/4] multi-angle lora ==="
pull Comfy-Org/Qwen-Image-Edit_ComfyUI split_files/loras/Qwen-Edit-2509-Multiple-angles.safetensors "$STAGE" || exit 1

echo "=== move staged files into shared model tree ==="
mv -f "$STAGE/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" "$REPO/models/text_encoders/"
mv -f "$STAGE/split_files/vae/qwen_image_vae.safetensors"                     "$REPO/models/vae/"
mv -f "$STAGE/split_files/loras/Qwen-Edit-2509-Multiple-angles.safetensors"   "$REPO/models/loras/"

echo "=== final sizes ==="
ls -la "$REPO/models/diffusion_models/Qwen-Image-Edit-2509-Q6_K.gguf" \
       "$REPO/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
       "$REPO/models/vae/qwen_image_vae.safetensors" \
       "$REPO/models/loras/Qwen-Edit-2509-Multiple-angles.safetensors"
echo "ALL_DONE"
