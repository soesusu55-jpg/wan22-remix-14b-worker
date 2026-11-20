# Wan2.2-Remix NSFW 14B — RunPod Serverless (ComfyUI)
# Base: official worker-comfyui base. Version pinned from Gusdev06's
# working Remix I2V 14B Dockerfile (2026-11-20).
FROM runpod/worker-comfyui:5.8.4-base

ARG HF_TOKEN=""
# Remix NSFW 14B — HIGH and LOW files. MUST be same version + same lighting.
# Verified low file on HF:
#   NSFW/Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors
# Check the exact high filename on the HF Files tab before building.
ARG MODEL_HIGH_FILE="Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors"
ARG MODEL_LOW_FILE="Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors"
ARG MODEL_REPO="FX-FeiHou/wan2.2-Remix"
ARG MODEL_SUBDIR="NSFW"

ENV HF_TOKEN=${HF_TOKEN}
ENV MODEL_HIGH_FILE=${MODEL_HIGH_FILE}
ENV MODEL_LOW_FILE=${MODEL_LOW_FILE}
ENV MODEL_REPO=${MODEL_REPO}
ENV COMFYUI_PATH=/comfyui
# 2026-11-20: the base image installs ComfyUI at /comfyui (lowercase,
# via `comfy --workspace /comfyui install`). /ComfyUI (capital C) does
# NOT exist there — an earlier build created it by mkdir and put the
# custom nodes and models in the wrong place, so the handler failed
# with "can't open file '/ComfyUI/main.py'". Everything below must use
# /comfyui.
# Build 7d57576c failed with "huggingface-cli: command not found" even
# though huggingface_hub 1.7.2 was installed in /opt/venv: /opt/venv/bin
# was not on PATH in the build shell. Put it first so `hf`, `pip` and
# `python3` all resolve to the venv consistently.
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir "huggingface_hub>=0.27" runpod && \
  (command -v hf >/dev/null && hf --version || echo "note: hf CLI not on PATH after install; download_models.sh falls back to the python API")

# Custom nodes required by api-workflow.json (same set as Gusdev06):
# FastUnsharpSharpen (comfyui-vrgamedevgirl), Seed (rgthree-comfy),
# KJNodes, and VideoHelperSuite (VHS_VideoCombine).
# NOTE: comfyui-vrgamedevgirl has no "0.1.0" tag (Gusdev06's checkout
# fails with "pathspec '0.1.0' did not match"), so it is pinned to the
# latest main commit instead. KJNodes / rgthree pins are commit SHAs.
RUN mkdir -p /comfyui/custom_nodes && cd /comfyui/custom_nodes && \
  git clone https://github.com/vrgamegirl19/comfyui-vrgamedevgirl && \
  cd comfyui-vrgamedevgirl && git checkout 5d73177f1a1e70d985f97c1e7a13fafa699e18ae && cd .. && \
  git clone https://github.com/kijai/ComfyUI-KJNodes && \
  cd ComfyUI-KJNodes && git checkout a6b867b63a29ca48ddb15c589e17a9f2d8530d57 && cd .. && \
  git clone https://github.com/rgthree/rgthree-comfy && \
  cd rgthree-comfy && git checkout 0fb1e239a903e93ef626a8c20589b38f46e39dff && cd .. && \
  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
  cd ComfyUI-VideoHelperSuite && git checkout 4d907bee61e92c2e65af3bd6383a4e4d356126d1 && cd .. && \
  for d in comfyui-vrgamedevgirl ComfyUI-KJNodes rgthree-comfy ComfyUI-VideoHelperSuite; do \
    if [ -f "$d/requirements.txt" ]; then pip install --no-cache-dir -r "$d/requirements.txt" || true; fi; \
  done

COPY download_models.sh /download_models.sh
RUN chmod +x /download_models.sh && /download_models.sh

COPY handler.py /handler.py
COPY api-workflow.json /api-workflow.json

WORKDIR /
CMD ["python3", "/handler.py"]
