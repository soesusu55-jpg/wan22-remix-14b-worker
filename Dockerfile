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
ENV COMFYUI_PATH=/ComfyUI

RUN pip install --no-cache-dir "huggingface_hub>=0.27" runpod

# Custom nodes required by api-workflow.json (same set as Gusdev06):
# FastUnsharpSharpen (comfyui-vrgamedevgirl), Seed (rgthree-comfy),
# KJNodes, and VideoHelperSuite (VHS_VideoCombine).
RUN cd /ComfyUI/custom_nodes && \
  git clone https://github.com/vrgamegirl19/comfyui-vrgamedevgirl && \
  cd comfyui-vrgamedevgirl && git checkout 0.1.0 && cd .. && \
  git clone https://github.com/kijai/ComfyUI-KJNodes && \
  cd ComfyUI-KJNodes && git checkout a6b867b63a29ca48ddb15c589e17a9f2d8530d57 && cd .. && \
  git clone https://github.com/rgthree/rgthree-comfy && \
  cd rgthree-comfy && git checkout 0fb1e239a903e93ef626a8c20589b38f46e39dff && cd .. && \
  for d in comfyui-vrgamedevgirl ComfyUI-KJNodes rgthree-comfy; do \
    if [ -f "$d/requirements.txt" ]; then pip install --no-cache-dir -r "$d/requirements.txt" || true; fi; \
  done
RUN comfy node install --exit-on-fail comfyui-videohelpersuite@1.6.1 --mode remote || comfy node install comfyui-videohelpersuite --mode remote || true

COPY download_models.sh /download_models.sh
RUN chmod +x /download_models.sh && /download_models.sh

COPY handler.py /handler.py
COPY api-workflow.json /api-workflow.json

WORKDIR /
CMD ["python3", "/handler.py"]
