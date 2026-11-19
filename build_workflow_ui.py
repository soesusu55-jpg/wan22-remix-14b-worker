"""Build UI-format workflow.json (FLF2V, 10s) from the API workflow.

UI format = nodes[] + links[] (ComfyUI canvas format).
API format (api-workflow.json) is for POST /prompt only and cannot be
dragged into the ComfyUI UI — it shows "workflow does not contain any nodes".
This script mirrors Gusdev06's workflow.json layout, with:
  - WanImageToVideo (107) -> WanFirstLastFrameToVideo (107)
  - LoadImage 106 = start_image.png, new LoadImage 108 = end_image.png
  - LoraLoaderModelOnly 109/110 removed (Blink LoRA)
  - length 33 -> 161 frames, 16 fps
"""
import json

POS_TEXT = "A smooth continuous video that begins at the first image and ends at the last image, natural motion, cinematic lighting, detailed"
NEG_TEXT = "low quality, worst quality, blurry, out of focus, motion blur, deformed, ugly, bad anatomy, extra limbs, mutated hands, poorly drawn hands, text, watermark, logo, censored, mosaic censor, black bars, plastic skin, doll-like, uncanny valley, overexposed, underexposed, bad lighting, flat lighting, jpeg artifacts, pixelated, noisy, grainy"

def node(id_, type_, pos, size, inputs, outputs, widgets, title=None, props=None, flags=None, order=0, color=None, bgcolor=None):
    n = {"id": id_, "type": type_, "pos": pos, "size": size, "flags": flags or {}, "order": order, "mode": 0,
         "inputs": inputs, "outputs": outputs, "properties": props or {}, "widgets_values": widgets}
    if title:
        n["title"] = title
    if color:
        n["color"] = color
    if bgcolor:
        n["bgcolor"] = bgcolor
    return n

def inp(name, type_, link=None, slot_index=None, shape=None, widget=None):
    d = {"name": name, "type": type_, "link": link}
    if slot_index is not None:
        d["slot_index"] = slot_index
    if shape is not None:
        d["shape"] = shape
    if widget:
        d["widget"] = widget
    return d

def out(name, type_, links, slot_index=0, shape=None, dir_=None):
    d = {"name": name, "type": type_, "links": links, "slot_index": slot_index}
    if shape is not None:
        d["shape"] = shape
    if dir_ is not None:
        d["dir"] = dir_
    return d

# links: [id, origin_id, origin_slot, target_id, target_slot, type]
links = [
    [76, 39, 0, 8, 1, "VAE"],
    [113, 57, 0, 58, 3, "LATENT"],
    [123, 55, 0, 58, 0, "MODEL"],
    [124, 58, 0, 8, 0, "LATENT"],
    [125, 54, 0, 57, 0, "MODEL"],
    [140, 68, 0, 57, 5, "INT"],
    [141, 68, 0, 58, 5, "INT"],
    [142, 67, 0, 57, 6, "INT"],
    [143, 67, 0, 58, 6, "INT"],
    [180, 97, 0, 6, 0, "CLIP"],
    [181, 97, 0, 7, 0, "CLIP"],
    [210, 8, 0, 104, 0, "IMAGE"],
    [211, 104, 0, 99, 0, "IMAGE"],
    [212, 105, 0, 57, 4, "INT"],
    [213, 105, 0, 58, 4, "INT"],
    [214, 106, 0, 107, 5, "IMAGE"],
    [215, 107, 0, 57, 1, "CONDITIONING"],
    [216, 107, 1, 57, 2, "CONDITIONING"],
    [217, 107, 2, 57, 3, "LATENT"],
    [218, 107, 0, 58, 1, "CONDITIONING"],
    [219, 107, 1, 58, 2, "CONDITIONING"],
    [220, 103, 0, 55, 0, "MODEL"],
    [221, 77, 0, 54, 0, "MODEL"],
    [222, 6, 0, 107, 0, "CONDITIONING"],
    [223, 7, 0, 107, 1, "CONDITIONING"],
    [224, 39, 0, 107, 2, "VAE"],
    [228, 108, 0, 107, 6, "IMAGE"],
]

nodes = [
    node(97, "CLIPLoader", [40, 230], [344, 106], [],
         [out("CLIP", "CLIP", [180, 181])],
         ["nsfw_wan_umt5-xxl_fp8_scaled.safetensors", "wan", "default"], order=0,
         props={"cnr_id": "comfy-core", "ver": "0.3.60"}),
    node(8, "VAEDecode", [1930, -120], [210, 46],
         [inp("samples", "LATENT", 124), inp("vae", "VAE", 76)],
         [out("IMAGE", "IMAGE", [210])], [], order=17, flags={"collapsed": True},
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(104, "FastUnsharpSharpen", [2080, -120], [315, 58],
         [inp("images", "IMAGE", 210)],
         [out("IMAGE", "IMAGE", [211])], [0.5, False], order=18, flags={"collapsed": True},
         props={"aux_id": "vrgamegirl19/comfyui-vrgamedevgirl", "ver": "0.1.0"}, color="#432", bgcolor="#653"),
    node(68, "INTConstant", [650, -80], [210, 58], [],
         [out("value", "INT", [140, 141])], [8], title="Steps", order=1,
         props={"cnr_id": "comfyui-kjnodes"}, color="#1b4669", bgcolor="#29699c"),
    node(54, "ModelSamplingSD3", [420, -80], [210, 60],
         [inp("model", "MODEL", 221)],
         [out("MODEL", "MODEL", [125])], [2], order=13,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(55, "ModelSamplingSD3", [420, 20], [210, 60],
         [inp("model", "MODEL", 220)],
         [out("MODEL", "MODEL", [123])], [2], order=14,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(39, "VAELoader", [40, 380], [344, 60], [],
         [out("VAE", "VAE", [76, 224])], ["wan_2.1_vae.safetensors"], order=2,
         props={"cnr_id": "comfy-core", "ver": "0.3.45", "models": [{"name": "wan_2.1_vae.safetensors", "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors", "directory": "vae"}]}),
    node(67, "INTConstant", [650, 20], [210, 58], [],
         [out("value", "INT", [142, 143])], [3], title="Split_step", order=3,
         props={"cnr_id": "comfyui-kjnodes"}, color="#1b4669", bgcolor="#29699c"),
    node(105, "Seed (rgthree)", [900, 540], [315, 130], [],
         [out("SEED", "INT", [212, 213], shape=3, dir_=4)], [-1, "", "", ""], order=4,
         props={"cnr_id": "rgthree-comfy", "randomMax": 1125899906842624, "randomMin": 0}),
    node(77, "UNETLoader", [40, -20], [344, 82], [],
         [out("MODEL", "MODEL", [221])],
         ["Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors", "fp8_e4m3fn"], order=5,
         props={"cnr_id": "comfy-core", "ver": "0.3.60"}),
    node(103, "UNETLoader", [40, 110], [344, 82], [],
         [out("MODEL", "MODEL", [220])],
         ["Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors", "fp8_e4m3fn"], order=6,
         props={"cnr_id": "comfy-core", "ver": "0.3.60"}),
    node(107, "WanFirstLastFrameToVideo", [900, 282], [315, 210],
         [inp("positive", "CONDITIONING", 222),
          inp("negative", "CONDITIONING", 223),
          inp("vae", "VAE", 224),
          inp("clip_vision_start_image", "CLIP_VISION_OUTPUT", None, shape=7),
          inp("clip_vision_end_image", "CLIP_VISION_OUTPUT", None, shape=7),
          inp("start_image", "IMAGE", 214, shape=7),
          inp("end_image", "IMAGE", 228, shape=7)],
         [out("positive", "CONDITIONING", [215, 218], 0),
          out("negative", "CONDITIONING", [216, 219], 1),
          out("latent", "LATENT", [217], 2)],
         [720, 1280, 161, 1], order=12,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(106, "LoadImage", [900, -90], [315, 314], [],
         [out("IMAGE", "IMAGE", [214], 0), out("MASK", "MASK", None, 1)],
         ["start_image.png", "image"], order=7,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(108, "LoadImage", [1250, -90], [315, 314], [],
         [out("IMAGE", "IMAGE", [228], 0), out("MASK", "MASK", None, 1)],
         ["end_image.png", "image"], order=7,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(58, "KSamplerAdvanced", [1570, -80], [320, 750],
         [inp("model", "MODEL", 123),
          inp("positive", "CONDITIONING", 218),
          inp("negative", "CONDITIONING", 219),
          inp("latent_image", "LATENT", 113),
          inp("noise_seed", "INT", 213, widget={"name": "noise_seed"}),
          inp("steps", "INT", 141, widget={"name": "steps"}),
          inp("start_at_step", "INT", 143, widget={"name": "start_at_step"})],
         [out("LATENT", "LATENT", [124])],
         ["disable", 0, "fixed", 8, 1, "euler", "simple", 3, 10000, "disable"], order=16,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(57, "KSamplerAdvanced", [1250, -80], [320, 750],
         [inp("model", "MODEL", 125),
          inp("positive", "CONDITIONING", 215),
          inp("negative", "CONDITIONING", 216),
          inp("latent_image", "LATENT", 217),
          inp("noise_seed", "INT", 212, widget={"name": "noise_seed"}),
          inp("steps", "INT", 140, widget={"name": "steps"}),
          inp("end_at_step", "INT", 142, widget={"name": "end_at_step"})],
         [out("LATENT", "LATENT", [113])],
         ["enable", -1, "randomize", 8, 1, "euler", "simple", 0, 3, "enable"], order=15,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}),
    node(6, "CLIPTextEncode", [430, 170], [430, 300],
         [inp("clip", "CLIP", 180)],
         [out("CONDITIONING", "CONDITIONING", [222])], [POS_TEXT],
         title="CLIP Text Encode (Positive Prompt)", order=8,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}, color="#232", bgcolor="#353"),
    node(7, "CLIPTextEncode", [430, 520], [430, 140],
         [inp("clip", "CLIP", 181)],
         [out("CONDITIONING", "CONDITIONING", [223])], [NEG_TEXT],
         title="CLIP Text Encode (Negative Prompt)", order=9,
         props={"cnr_id": "comfy-core", "ver": "0.3.45"}, color="#322", bgcolor="#533"),
    node(99, "VHS_VideoCombine", [1910, -80], [390, 1005],
         [inp("images", "IMAGE", 211),
          inp("audio", "AUDIO", None, shape=7),
          inp("meta_batch", "VHS_BatchManager", None, shape=7),
          inp("vae", "VAE", None, shape=7)],
         [out("Filenames", "VHS_FILENAMES", None)],
         {"frame_rate": 16, "loop_count": 0, "filename_prefix": "%date:yyyy-MM-dd%/%date:yyyyMMdd_hhmmss%_Wan2.2", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": True, "trim_to_audio": False, "pingpong": False, "save_output": True},
         order=19, props={"cnr_id": "comfyui-videohelpersuite", "ver": "1.6.1"}),
]

wf = {
    "id": "wan22-remix-14b-flf2v-10s",
    "revision": 0,
    "last_node_id": 108,
    "last_link_id": 228,
    "nodes": nodes,
    "links": links,
    "groups": [
        {"id": 1, "title": "Step1 - Load models", "bounding": [30, -110, 370, 570], "color": "#3f789e", "font_size": 24, "flags": {}},
        {"id": 3, "title": "Step3 - Prompt", "bounding": [420, 100, 460, 580], "color": "#3f789e", "font_size": 24, "flags": {}},
    ],
    "config": {},
    "extra": {"ds": {"scale": 0.106, "offset": [9854, 6207]}, "frontendVersion": "1.41.21", "VHS_latentpreview": False, "VHS_latentpreviewrate": 0},
    "version": 0.4,
}

with open("workflow.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False)
print("wrote workflow.json, nodes:", len(nodes), "links:", len(links))
