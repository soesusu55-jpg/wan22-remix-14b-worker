#!/bin/bash
# POSIX-sh safe as well: do not use ${VAR:+...} with nested quotes or
# bash-only options, because the build may run this script under /bin/sh
# (dash rejects nested quotes inside ${...:+...} with "bad substitution").
set -eu

# hf_download wrapper: adds --token only when HF_TOKEN is set.
# Usage: hf_download <repo> <file> --local-dir <dir>
# NOTE (2026-11-20): build 7d57576c failed with
#   "/download_models.sh: line 13: huggingface-cli: command not found"
# even though the build log showed huggingface_hub 1.7.2 installed in
# /opt/venv. Two causes stack up: (1) huggingface-cli was removed in
# huggingface_hub 1.0, replaced by `hf`; (2) /opt/venv/bin may not be
# on PATH in the build shell, so neither CLI name is found. The
# `hf`-only fallback added after that failure would hit the same
# PATH problem, so this version does NOT rely on PATH alone:
#   1. try `hf` / `huggingface-cli` on PATH, then /opt/venv/bin/<name>;
#   2. fall back to the Python API (hf_hub_download) with the venv
#      interpreter first (/opt/venv/bin/python3), which bypasses the
#      CLI name and PATH entirely. The API is stable across
#      huggingface_hub 0.27-2.x, unlike the CLI name.
hf_download() {
  _repo="$1"; _file="$2"; _destdir=""
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --local-dir) _destdir="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  if [ -z "$_destdir" ]; then
    echo "hf_download: --local-dir is required." >&2
    exit 1
  fi
  # 1) CLI, on PATH or at its known venv location. A CLI that exists
  # but fails (e.g. a stale wrapper) falls through to the next method
  # instead of aborting the build.
  for _cmd in hf huggingface-cli /opt/venv/bin/hf /opt/venv/bin/huggingface-cli; do
    if command -v "$_cmd" >/dev/null 2>&1; then
      if [ -n "${HF_TOKEN:-}" ]; then
        _dl_ok=1; "$_cmd" download "$_repo" "$_file" --local-dir "$_destdir" --token "$HF_TOKEN" && _dl_ok=0 || true
      else
        _dl_ok=1; "$_cmd" download "$_repo" "$_file" --local-dir "$_destdir" && _dl_ok=0 || true
      fi
      if [ "$_dl_ok" = 0 ]; then return 0; fi
      echo "warning: '$_cmd download' failed for $_repo $_file; trying the next download method." >&2
    fi
  done
  # 2) Python API fallback. Check the import first so a python without
  # huggingface_hub just moves on to the next interpreter instead of
  # masking a real download failure.
  for _py in /opt/venv/bin/python3 /opt/venv/bin/python python3 python; do
    if command -v "$_py" >/dev/null 2>&1 && "$_py" -c "import huggingface_hub" 2>/dev/null; then
      echo "hf CLI not found; downloading via python ($_py) + hf_hub_download: $_repo $_file"
      HF_DL_REPO="$_repo" HF_DL_FILE="$_file" HF_DL_DIR="$_destdir" "$_py" -c 'import os, shutil
from huggingface_hub import hf_hub_download
p = hf_hub_download(repo_id=os.environ["HF_DL_REPO"], filename=os.environ["HF_DL_FILE"], token=os.environ.get("HF_TOKEN") or None)
dest = os.path.join(os.environ["HF_DL_DIR"], os.environ["HF_DL_FILE"])
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.copyfile(p, dest)'
      return 0
    fi
  done
  echo "No usable HF download method found: no hf/huggingface-cli on PATH or in /opt/venv/bin, and no python with huggingface_hub." >&2
  exit 1
}

# Download ONLY the files needed for Remix NSFW 14B.
# Do NOT download the whole FX-FeiHou/wan2.2-Remix repo (314GB total).
#
# Required env (set via Dockerfile ARG / .env):
#   MODEL_REPO       default: FX-FeiHou/wan2.2-Remix
#   MODEL_SUBDIR     default: NSFW
#   MODEL_HIGH_FILE  e.g. Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors
#   MODEL_LOW_FILE   e.g. Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors
#                    *** CHECK both exact filenames on the HF Files tab first ***
#                    *** Keep version (v3.0) and lighting the same for both ***
#   HF_TOKEN         only if the repo is gated / private

MODEL_REPO="${MODEL_REPO:-FX-FeiHou/wan2.2-Remix}"
MODEL_SUBDIR="${MODEL_SUBDIR:-NSFW}"
MODEL_HIGH_FILE="${MODEL_HIGH_FILE:-}"
MODEL_LOW_FILE="${MODEL_LOW_FILE:-}"

if [ -z "$MODEL_HIGH_FILE" ] || [ -z "$MODEL_LOW_FILE" ]; then
  echo "MODEL_HIGH_FILE / MODEL_LOW_FILE are required." >&2
  exit 1
fi

mkdir -p /comfyui/models/diffusion_models /comfyui/models/text_encoders /comfyui/models/vae /comfyui/models/loras

echo "Downloading Remix 14B HIGH: $MODEL_HIGH_FILE"
hf_download "$MODEL_REPO" "$MODEL_SUBDIR/$MODEL_HIGH_FILE" \
  --local-dir /tmp/remix
cp "/tmp/remix/$MODEL_SUBDIR/$MODEL_HIGH_FILE" "/comfyui/models/diffusion_models/$MODEL_HIGH_FILE"

echo "Downloading Remix 14B LOW: $MODEL_LOW_FILE"
hf_download "$MODEL_REPO" "$MODEL_SUBDIR/$MODEL_LOW_FILE" \
  --local-dir /tmp/remix
cp "/tmp/remix/$MODEL_SUBDIR/$MODEL_LOW_FILE" "/comfyui/models/diffusion_models/$MODEL_LOW_FILE"

echo "Downloading NSFW-tuned umt5 fp8 text encoder (Osrivers, as used by Gusdev06)"
# api-workflow.json CLIPLoader expects nsfw_wan_umt5-xxl_fp8_scaled.safetensors.
# Standard Kijai umt5_xxl_fp8_e4m3fn_scaled.safetensors is the non-NSFW alternative;
# do not mix the two filenames.
hf_download Osrivers/nsfw_wan_umt5-xxl_fp8_scaled.safetensors nsfw_wan_umt5-xxl_fp8_scaled.safetensors \
  --local-dir /tmp/t5
cp /tmp/t5/nsfw_wan_umt5-xxl_fp8_scaled.safetensors /comfyui/models/text_encoders/

echo "Downloading wan_2.1_vae (14B models use this, NOT wan2.2_vae)"
hf_download Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan_2.1_vae.safetensors \
  --local-dir /tmp/vae
cp /tmp/vae/split_files/vae/wan_2.1_vae.safetensors /comfyui/models/vae/ || \
  cp /tmp/vae/wan_2.1_vae.safetensors /comfyui/models/vae/

# Optional: LightX2V 4-step LoRAs for I2V 14B.
# Uncomment if your workflow uses them AND the Remix checkpoint does not already include Lightning.
# hf_download Kijai/WanVideo_comfy Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors --local-dir /tmp/lora
# cp /tmp/lora/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors /comfyui/models/loras/

rm -rf /tmp/remix /tmp/t5 /tmp/vae /tmp/lora
ls -lh /comfyui/models/diffusion_models/ /comfyui/models/text_encoders/ /comfyui/models/vae/
echo "Done."
