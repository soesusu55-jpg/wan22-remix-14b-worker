"""
RunPod Serverless handler for Wan2.2-Remix NSFW 14B (ComfyUI, FLF2V MoE pair).

Flow:
  1. Start ComfyUI in background (if not already running)
  2. Wait for http://127.0.0.1:8188/system_stats
  3. POST the API workflow to /prompt
  4. Poll /history/<prompt_id> until done (with timeout)
  5. Read the output video and return it as base64

Default workflow is api-workflow.json in this folder: FLF2V
(First-Last Frame to Video), 720x1280, 161 frames at 16 fps = ~10 s.
WanFirstLastFrameToVideo uses the ordinary I2V-A14B experts; there is
no dedicated FLF2V model for Wan 2.2.

Input (job["input"]):
  {
    "workflow": { ... ComfyUI API workflow JSON ... },  # optional, or use api-workflow.json
    "prompt": "optional text override (positive)",
    "negative_prompt": "optional text override (negative)",
    "start_image_b64": "base64 start image (also accepts 'image_b64')",
    "end_image_b64": "base64 end image",
    "timeout": 1800
  }

Notes:
  - 14B is a MoE PAIR: high-noise + low-noise experts, loaded in sequence.
    The workflow must have two UNETLoader nodes, one per file.
  - Returning base64 video is fine for testing. For production, upload the
    mp4 to S3/R2 here and return the URL instead (see TODO in _read_output).
  - Adults only, fictional only. No real-person deepfakes.
"""
import base64
import json
import os
import subprocess
import time

import requests
import runpod

COMFY_URL = os.environ.get("COMFY_API_URL", "http://127.0.0.1:8188")
COMFY_PATH = os.environ.get("COMFYUI_PATH", "/comfyui")
MODEL_HIGH_FILE = os.environ.get(
    "MODEL_HIGH_FILE",
    "Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors",
)
MODEL_LOW_FILE = os.environ.get(
    "MODEL_LOW_FILE",
    "Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors",
)

_proc = None
_COMFY_LOG = "/tmp/comfyui.log"


def _comfy_log_tail(nchars=3000):
    try:
        with open(_COMFY_LOG, encoding="utf-8", errors="replace") as f:
            data = f.read()
        return data[-nchars:]
    except Exception:
        return "(could not read ComfyUI log)"


def _start_comfyui():
    global _proc
    if _proc is not None and _proc.poll() is None:
        return
    # Skip auto-launch inside worker-comfyui if set; we launch explicitly.
    # NOTE (2026-11-20): do NOT use stdout=PIPE without a reader — the
    # child can block once the pipe fills, and its output is invisible.
    # Redirect to a log file instead, and surface its tail in errors so
    # a failed startup is diagnosable from the job error itself.
    logf = open(_COMFY_LOG, "a", encoding="utf-8")
    _proc = subprocess.Popen(
        ["python3", "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd=COMFY_PATH,
        stdout=logf,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Cold start (torch + ComfyUI + custom nodes) can take minutes on a
    # fresh worker; 180s was too short and hid the real cause.
    deadline = time.time() + 600
    while time.time() < deadline:
        if _proc.poll() is not None:
            raise RuntimeError(
                f"ComfyUI exited early with code {_proc.returncode}.\n"
                f"Log tail:\n{_comfy_log_tail()}"
            )
        try:
            r = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(
        f"ComfyUI did not become ready in 600s.\nLog tail:\n{_comfy_log_tail()}"
    )


def _load_default_workflow():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("api-workflow.json", "workflow.json"):
        p = os.path.join(here, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise RuntimeError("No workflow JSON found. Pass 'workflow' in input.")


def _read_output(prompt_id):
    r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=30)
    r.raise_for_status()
    hist = r.json().get(prompt_id, {})
    for node_id, node_out in hist.get("outputs", {}).items():
        for item in node_out.get("videos", []) + node_out.get("images", []):
            filename = item.get("filename")
            subfolder = item.get("subfolder", "")
            ftype = item.get("type", "output")
            if not filename:
                continue
            # Fetch via /view
            vr = requests.get(
                f"{COMFY_URL}/view",
                params={"filename": filename, "subfolder": subfolder, "type": ftype},
                timeout=60,
            )
            if vr.status_code == 200:
                # TODO (production): upload vr.content to S3/R2 and return URL.
                return {
                    "filename": filename,
                    "content_type": vr.headers.get("content-type", "video/mp4"),
                    "data_b64": base64.b64encode(vr.content).decode("ascii"),
                }
    return None


def handler(job):
    inp = job.get("input") or {}
    timeout = int(inp.get("timeout", 1800))

    _start_comfyui()

    workflow = inp.get("workflow") or _load_default_workflow()

    # Text overrides: first CLIPTextEncode = positive, second = negative.
    if inp.get("prompt") or inp.get("negative_prompt"):
        encodes = [
            node
            for node in workflow.values()
            if node.get("class_type") == "CLIPTextEncode" and "inputs" in node
        ]
        if inp.get("prompt") and encodes:
            encodes[0]["inputs"]["text"] = inp["prompt"]
        if inp.get("negative_prompt") and len(encodes) > 1:
            encodes[1]["inputs"]["text"] = inp["negative_prompt"]

    # Start / end images for FLF2V. The workflow references these filenames;
    # see api-workflow.json nodes 106 (start_image.png) and 108 (end_image.png).
    # "image_b64" is kept as an alias for the start image.
    for key, filename in (
        ("start_image_b64", "start_image.png"),
        ("image_b64", "start_image.png"),
        ("end_image_b64", "end_image.png"),
    ):
        if inp.get(key):
            img_path = os.path.join(COMFY_PATH, "input", filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(inp[key]))

    # 2026-11-20: surface ComfyUI's /prompt error body. The first 400 here
    # ("Bad Request") hid which node/input was invalid; raise_for_status()
    # alone discards the body that names it.
    resp = requests.post(
        f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=60
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"ComfyUI /prompt failed ({resp.status_code}): {resp.text[:3000]}"
        )
    prompt_id = resp.json()["prompt_id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(5)
        out = _read_output(prompt_id)
        if out:
            return {
                "status": "completed",
                "model_high_file": MODEL_HIGH_FILE,
                "model_low_file": MODEL_LOW_FILE,
                "prompt_id": prompt_id,
                "video": out,
            }
        # Check for failure via history status
        try:
            h = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10).json()
            if h.get(prompt_id, {}).get("status", {}).get("status_str") == "error":
                return {"status": "error", "prompt_id": prompt_id, "history": h}
        except Exception:
            pass

    return {"status": "timeout", "prompt_id": prompt_id}


runpod.serverless.start({"handler": handler})
