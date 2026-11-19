#!/bin/bash
set -euo pipefail

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

mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/text_encoders /ComfyUI/models/vae /ComfyUI/models/loras

echo "Downloading Remix 14B HIGH: $MODEL_HIGH_FILE"
huggingface-cli download "$MODEL_REPO" "$MODEL_SUBDIR/$MODEL_HIGH_FILE" \
  --local-dir /tmp/remix \
  ${HF_TOKEN:+--token "$HF_TOKEN"}
cp "/tmp/remix/$MODEL_SUBDIR/$MODEL_HIGH_FILE" "/ComfyUI/models/diffusion_models/$MODEL_HIGH_FILE"

echo "Downloading Remix 14B LOW: $MODEL_LOW_FILE"
huggingface-cli download "$MODEL_REPO" "$MODEL_SUBDIR/$MODEL_LOW_FILE" \
  --local-dir /tmp/remix \
  ${HF_TOKEN:+--token "$HF_TOKEN"}
cp "/tmp/remix/$MODEL_SUBDIR/$MODEL_LOW_FILE" "/ComfyUI/models/diffusion_models/$MODEL_LOW_FILE"

echo "Downloading NSFW-tuned umt5 fp8 text encoder (Osrivers, as used by Gusdev06)"
# api-workflow.json CLIPLoader expects nsfw_wan_umt5-xxl_fp8_scaled.safetensors.
# Standard Kijai umt5_xxl_fp8_e4m3fn_scaled.safetensors is the non-NSFW alternative;
# do not mix the two filenames.
huggingface-cli download Osrivers/nsfw_wan_umt5-xxl_fp8_scaled.safetensors nsfw_wan_umt5-xxl_fp8_scaled.safetensors \
  --local-dir /tmp/t5 \
  ${HF_TOKEN:+--token "$HF_TOKEN"}
cp /tmp/t5/nsfw_wan_umt5-xxl_fp8_scaled.safetensors /ComfyUI/models/text_encoders/

echo "Downloading wan_2.1_vae (14B models use this, NOT wan2.2_vae)"
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan_2.1_vae.safetensors \
  --local-dir /tmp/vae \
  ${HF_TOKEN:+--token "$HF_TOKEN"}
cp /tmp/vae/split_files/vae/wan_2.1_vae.safetensors /ComfyUI/models/vae/ || \
  cp /tmp/vae/wan_2.1_vae.safetensors /ComfyUI/models/vae/

# Optional: LightX2V 4-step LoRAs for I2V 14B.
# Uncomment if your workflow uses them AND the Remix checkpoint does not already include Lightning.
# huggingface-cli download Kijai/WanVideo_comfy Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors --local-dir /tmp/lora
# cp /tmp/lora/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors /ComfyUI/models/loras/

rm -rf /tmp/remix /tmp/t5 /tmp/vae /tmp/lora
ls -lh /ComfyUI/models/diffusion_models/ /ComfyUI/models/text_encoders/ /ComfyUI/models/vae/
echo "Done."
