#!/usr/bin/env python3
"""
install_models.py — Bootstrap the full image_gen model library from scratch.

Checks what's missing, verifies disk space, then downloads everything
with resume support, smart ETAs, and minimal output.

Usage:
    python3 scripts/install_models.py              # full install
    python3 scripts/install_models.py --check      # show missing + disk needed, exit
    python3 scripts/install_models.py --only loras # only download a section
    python3 scripts/install_models.py --skip wan   # skip a section (e.g. 120GB WAN)

Requires:
    $CIVITAI_API_KEY  or  ~/.civitai_token
    ~/.cache/huggingface/token  (or $HF_TOKEN)
"""

import os, sys, time, subprocess, argparse, shutil
from pathlib import Path

REPO = Path(__file__).parent.parent
MODELS = REPO / "models"
LOG = REPO / "install_models.log"

HF = "https://huggingface.co"
CV = "https://civitai.com/api/download/models"

# ─── FORMAT HELPERS ───────────────────────────────────────────────────────────

def fmt_size(b):
    if b >= 1_073_741_824: return f"{b/1_073_741_824:.1f}G"
    if b >= 1_048_576:     return f"{b/1_048_576:.0f}M"
    return f"{b/1024:.0f}K"

def fmt_eta(secs):
    if secs < 0:      return "?"
    if secs < 60:     return f"{secs:.0f}s"
    if secs < 3600:   return f"{secs/60:.0f}m"
    h = int(secs // 3600); m = int((secs % 3600) // 60)
    return f"{h}h {m}m"

def fmt_rate(bps):
    if bps >= 1_048_576: return f"{bps/1_048_576:.1f} MB/s"
    return f"{bps/1024:.0f} KB/s"

# ─── CATALOG ──────────────────────────────────────────────────────────────────
# Each entry: {
#   "name":    display name
#   "dest":    path relative to models/
#   "size":    expected bytes (0 = skip size check)
#   "url":     download URL — use {hf_token} and {cv_token} placeholders
#              OR "civitai:{model_id}" to auto-resolve latest version
#   "section": grouping label (used with --only / --skip)
# }

def catalog(hf_token, cv_token):
    def hf(repo, file): return f"{HF}/{repo}/resolve/main/{file}"
    def cv(version_id): return f"{CV}/{version_id}?token={cv_token}"

    return [

        # ── Checkpoints ──────────────────────────────────────────────────────
        {"section": "checkpoints", "name": "Illustrious XL v0.1",
         "dest": "checkpoints/Illustrious-XL-v0.1.safetensors",
         "size": 6_979_321_856,
         "url":  hf("OnomaAIResearch/Illustrious-xl-early-release-v0",
                    "Illustrious-XL-v0.1.safetensors"),
         "auth": hf_token},

        {"section": "checkpoints", "name": "SVD-XT",
         "dest": "checkpoints/svd_xt.safetensors",
         "size": 9_559_625_980,
         "url":  hf("stabilityai/stable-video-diffusion-img2vid-xt",
                    "svd_xt.safetensors"),
         "auth": hf_token},

        # ── Diffusion Models (Flux) ───────────────────────────────────────────
        {"section": "flux", "name": "Flux.1-dev",
         "dest": "diffusion_models/flux1-dev.safetensors",
         "size": 23_804_823_040,
         "url":  hf("black-forest-labs/FLUX.1-dev", "flux1-dev.safetensors"),
         "auth": hf_token},

        {"section": "flux", "name": "Flux.1-Canny-dev",
         "dest": "diffusion_models/flux1-canny-dev.safetensors",
         "size": 11_903_238_144,
         "url":  hf("black-forest-labs/FLUX.1-Canny-dev",
                    "flux1-canny-dev.safetensors"),
         "auth": hf_token},

        {"section": "flux", "name": "Flux.1-Depth-dev",
         "dest": "diffusion_models/flux1-depth-dev.safetensors",
         "size": 11_903_238_144,
         "url":  hf("black-forest-labs/FLUX.1-Depth-dev",
                    "flux1-depth-dev.safetensors"),
         "auth": hf_token},

        {"section": "flux", "name": "Flux.1-Kontext-dev",
         "dest": "diffusion_models/flux1-kontext-dev.safetensors",
         "size": 23_802_947_360,
         "url":  hf("black-forest-labs/FLUX.1-Kontext-dev",
                    "flux1-kontext-dev.safetensors"),
         "auth": hf_token},

        # ── HunyuanVideo ─────────────────────────────────────────────────────
        {"section": "hunyuan", "name": "HunyuanVideo transformer FP8",
         "dest": "diffusion_models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors",
         "size": 13_000_000_000,
         "url":  hf("Kijai/HunyuanVideo_comfy",
                    "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors"),
         "auth": hf_token},

        {"section": "hunyuan", "name": "HunyuanVideo VAE",
         "dest": "vae/hunyuan/pytorch_model.pt",
         "size": 941_000_000,
         "url":  hf("tencent/HunyuanVideo",
                    "hunyuan-video-t2v-720p/vae/pytorch_model.pt"),
         "auth": hf_token},

        {"section": "hunyuan", "name": "llava-llama-3-8b shard 1/4",
         "dest": "text_encoders/llava-llama-3-8b/model-00001-of-00004.safetensors",
         "size": 4_977_222_880,
         "url":  hf("Kijai/llava-llama-3-8b-text-encoder-tokenizer",
                    "model-00001-of-00004.safetensors"),
         "auth": hf_token},

        {"section": "hunyuan", "name": "llava-llama-3-8b shard 2/4",
         "dest": "text_encoders/llava-llama-3-8b/model-00002-of-00004.safetensors",
         "size": 4_999_802_616,
         "url":  hf("Kijai/llava-llama-3-8b-text-encoder-tokenizer",
                    "model-00002-of-00004.safetensors"),
         "auth": hf_token},

        {"section": "hunyuan", "name": "llava-llama-3-8b shard 3/4",
         "dest": "text_encoders/llava-llama-3-8b/model-00003-of-00004.safetensors",
         "size": 4_915_916_080,
         "url":  hf("Kijai/llava-llama-3-8b-text-encoder-tokenizer",
                    "model-00003-of-00004.safetensors"),
         "auth": hf_token},

        {"section": "hunyuan", "name": "llava-llama-3-8b shard 4/4",
         "dest": "text_encoders/llava-llama-3-8b/model-00004-of-00004.safetensors",
         "size": 1_100_000_000,
         "url":  hf("Kijai/llava-llama-3-8b-text-encoder-tokenizer",
                    "model-00004-of-00004.safetensors"),
         "auth": hf_token},

        # ── WAN 2.2 I2V ──────────────────────────────────────────────────────
        *[{"section": "wan",
           "name":  f"WAN 2.2 high_noise shard {i}/6",
           "dest":  f"diffusion_models/wan2.2-i2v/high_noise/"
                    f"diffusion_pytorch_model-{i:05d}-of-00006.safetensors",
           "size":  7_595_559_224 if i == 6 else 9_839_059_744 if i >= 4 else 9_943_979_184 if i >= 2 else 9_994_119_944,
           "url":   hf("Wan-AI/Wan2.2-I2V-A14B",
                       f"high_noise_model/diffusion_pytorch_model-{i:05d}-of-00006.safetensors"),
           "auth":  hf_token}
          for i in range(1, 7)],

        *[{"section": "wan",
           "name":  f"WAN 2.2 low_noise shard {i}/6",
           "dest":  f"diffusion_models/wan2.2-i2v/low_noise/"
                    f"diffusion_pytorch_model-{i:05d}-of-00006.safetensors",
           "size":  7_595_559_224 if i == 6 else 9_839_059_744 if i >= 4 else 9_943_979_184 if i >= 2 else 9_994_119_944,
           "url":   hf("Wan-AI/Wan2.2-I2V-A14B",
                       f"low_noise_model/diffusion_pytorch_model-{i:05d}-of-00006.safetensors"),
           "auth":  hf_token}
          for i in range(1, 7)],

        {"section": "wan", "name": "WAN 2.2 T5 encoder",
         "dest": "text_encoders/wan-umt5-xxl-enc-bf16.pth",
         "size": 11_361_920_418,
         "url":  hf("Wan-AI/Wan2.2-I2V-A14B", "models_t5_umt5-xxl-enc-bf16.pth"),
         "auth": hf_token},

        {"section": "wan", "name": "WAN 2.2 VAE",
         "dest": "vae/wan/Wan2.1_VAE.pth",
         "size": 507_609_880,
         "url":  hf("Wan-AI/Wan2.2-I2V-A14B", "Wan2.1_VAE.pth"),
         "auth": hf_token},

        # ── VAE ──────────────────────────────────────────────────────────────
        {"section": "vae", "name": "SDXL VAE fp16-fix",
         "dest": "vae/sdxl.vae.safetensors",
         "size": 334_641_162,
         "url":  hf("madebyollin/sdxl-vae-fp16-fix", "sdxl.vae.safetensors"),
         "auth": hf_token},

        {"section": "vae", "name": "Flux AE",
         "dest": "vae/flux-ae.safetensors",
         "size": 334_643_202,
         "url":  hf("black-forest-labs/FLUX.1-dev", "ae.safetensors"),
         "auth": hf_token},

        # ── Text Encoders ─────────────────────────────────────────────────────
        {"section": "encoders", "name": "CLIP-L (Flux)",
         "dest": "text_encoders/clip_l.safetensors",
         "size": 246_144_152,
         "url":  hf("comfyanonymous/flux_text_encoders", "clip_l.safetensors"),
         "auth": hf_token},

        {"section": "encoders", "name": "T5-XXL FP8 (Flux)",
         "dest": "text_encoders/t5xxl_fp8_e4m3fn.safetensors",
         "size": 4_891_624_992,
         "url":  hf("comfyanonymous/flux_text_encoders",
                    "t5xxl_fp8_e4m3fn.safetensors"),
         "auth": hf_token},

        # ── Style Models + Clip Vision ────────────────────────────────────────
        {"section": "flux", "name": "Flux Redux",
         "dest": "style_models/flux1-redux-dev.safetensors",
         "size": 130_000_000,
         "url":  hf("black-forest-labs/FLUX.1-Redux-dev",
                    "flux1-redux-dev.safetensors"),
         "auth": hf_token},

        {"section": "flux", "name": "SigCLIP Vision (Redux)",
         "dest": "clip_vision/sigclip_vision_patch14_384.safetensors",
         "size": 856_000_000,
         "url":  hf("Comfy-Org/sigclip_vision_384",
                    "sigclip_vision_patch14_384.safetensors"),
         "auth": hf_token},

        # ── ControlNet ────────────────────────────────────────────────────────
        {"section": "controlnet", "name": "Flux Depth ControlNet v3 (XLabs)",
         "dest": "controlnet/flux-depth-controlnet-v3.safetensors",
         "size": 1_400_000_000,
         "url":  hf("XLabs-AI/flux-controlnet-depth-v3",
                    "flux-depth-controlnet-v3.safetensors"),
         "auth": hf_token},

        {"section": "controlnet", "name": "Flux Canny ControlNet v3 (XLabs)",
         "dest": "controlnet/flux-canny-controlnet-v3.safetensors",
         "size": 1_400_000_000,
         "url":  hf("XLabs-AI/flux-controlnet-canny-v3",
                    "flux-canny-controlnet-v3.safetensors"),
         "auth": hf_token},

        {"section": "controlnet", "name": "OpenPose XL2 (SDXL)",
         "dest": "controlnet/OpenPoseXL2.safetensors",
         "size": 4_700_000_000,
         "url":  hf("thibaud/controlnet-openpose-sdxl-1.0",
                    "OpenPoseXL2.safetensors"),
         "auth": hf_token},

        {"section": "controlnet", "name": "ControlNet Union Pro (Shakker-Labs)",
         "dest": "controlnet/flux-controlnet-union-pro-shakker.safetensors",
         "size": 6_603_953_920,
         "url":  hf("Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro",
                    "diffusion_pytorch_model.safetensors"),
         "auth": hf_token},

        {"section": "controlnet", "name": "OpenPose ControlNet (Flux)",
         "dest": "controlnet/flux-openpose-controlnet.safetensors",
         "size": 2_975_238_096,
         "url":  hf("raulc0399/flux_dev_openpose_controlnet",
                    "model.safetensors"),
         "auth": hf_token},

        {"section": "controlnet", "name": "ControlNet Union (InstantX)",
         "dest": "controlnet/flux-controlnet-union-instantx.safetensors",
         "size": 6_603_953_920,
         "url":  hf("InstantX/FLUX.1-dev-Controlnet-Union",
                    "diffusion_pytorch_model.safetensors"),
         "auth": hf_token},

        # ── Upscalers ─────────────────────────────────────────────────────────
        {"section": "upscalers", "name": "4x-UltraSharp",
         "dest": "upscale_models/4x-UltraSharp.pth",
         "size": 67_040_256,
         "url":  f"{CV}/125843?token={cv_token}"},

        {"section": "upscalers", "name": "RealESRGAN x4plus",
         "dest": "upscale_models/RealESRGAN_x4plus.pth",
         "size": 67_040_256,
         "url":  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"},

        {"section": "upscalers", "name": "4x-AnimeSharp",
         "dest": "upscale_models/4x-AnimeSharp.pth",
         "size": 67_040_256,
         "url":  hf("f5aiteam/Upscaler_Models", "4x-AnimeSharp.pth"),
         "auth": hf_token},

        # ── AnimateDiff ───────────────────────────────────────────────────────
        {"section": "animatediff", "name": "AnimateDiff motion adapter v1.5-3",
         "dest": "animatediff_models/mm_sd_v15_v3.safetensors",
         "size": 1_600_000_000,
         "url":  hf("guoyww/animatediff-motion-adapter-v1-5-3",
                    "mm_sd_v15_v3.safetensors"),
         "auth": hf_token},

        *[{"section": "animatediff",
           "name": f"AnimateDiff camera LoRA: {name}",
           "dest": f"animatediff_motion_lora/{fname}",
           "size": 118_000_000,
           "url":  hf("Cseti/Basic_camera_motion_LoRAs_sd15-ad2-v1", fname),
           "auth": hf_token}
          for fname, name in [
              ("1600_cseti_1077723_camera-zoomin-10vid_mv2.safetensors",  "ZoomIn"),
              ("1600_cseti_9192119_camera-zoomout-10vid_mv2.safetensors", "ZoomOut"),
              ("1600_cseti_9213319_camera-lateral_left-10vid_mv2.safetensors",  "PanLeft"),
              ("1600_cseti_6664682_camera-lateral_right-10vid_mv2.safetensors", "PanRight"),
              ("1600_cseti_1720230_camera-crane_up-10vid_mv2.safetensors",   "TiltUp"),
              ("1600_cseti_9406077_camera-crane_down-10vid_mv2.safetensors", "TiltDown"),
              ("2800_cseti_1093371_camera-zoomin-32f-10vid_mv2.safetensors", "ZoomIn-32f"),
          ]],

        # ── Flux LoRAs (Anime / Illustration / Cartoon / Graphic) ─────────────
        *[{"section": "loras", "name": name, "dest": f"loras/{fname}",
           "size": 0, "url": cv(vid)}
          for name, fname, vid in [
              ("Anime CRABDM",        "Anime-CRABDM-Flux.safetensors",          2534815),
              ("Neurocore ShadowCircuit", "Neurocore-ShadowCircuit-Flux.safetensors", 2459399),
              ("RetroAnime",          "RetroAnime-Flux.safetensors",            806265),
              ("FluxMyth SharpL1nes", "FluxMythSharpL1nes.safetensors",         2620790),
              ("Illustration Concept","IllustrationConcept-Flux.safetensors",   2793131),
              ("Painterly Fantasy",   "PainterlyFantasy-Flux.safetensors",      1189379),
              ("Character Design V2", "CharacterDesign-FluxV2.safetensors",     2500612),
              ("Disney Studios",      "Disney-Studios-Flux.safetensors",        2494747),
              ("Comic Book Page",     "ComicBookPage-Flux.safetensors",         2544182),
              ("Swiss Design",        "SwissDesign-Flux.safetensors",           913310),
              ("Milton Glaser",       "MiltonGlaser-Flux.safetensors",          1003311),
              ("Graffiti Logo",       "GraffitiLogo-Flux.safetensors",          935989),
              ("Logo Maker 1024",     "LogoMaker1024-Flux.safetensors",         846937),
          ]],

        # ── Storyboarding + Noir LoRAs ────────────────────────────────────────
        {"section": "loras", "name": "Film Storyboard In-Context",
         "dest": "loras/film-storyboard.safetensors",
         "size": 180_000_000,
         "url":  hf("ali-vilab/In-Context-LoRA", "film-storyboard.safetensors"),
         "auth": hf_token},

        {"section": "loras", "name": "QWEN Next Scene v2",
         "dest": "loras/QwenNextScene-v2.safetensors",
         "size": 309_000_000,
         "url":  hf("lovis93/next-scene-qwen-image-lora-2509",
                    "next-scene_lora-v2-3000.safetensors"),
         "auth": hf_token},

        {"section": "loras", "name": "XLabs IP-Adapter v2",
         "dest": "loras/flux-ip-adapter-v2-xlabs.safetensors",
         "size": 1_057_356_424,
         "url":  hf("XLabs-AI/flux-ip-adapter-v2", "ip_adapter.safetensors"),
         "auth": hf_token},

        *[{"section": "loras", "name": name, "dest": f"loras/{fname}",
           "size": 0, "url": cv(vid)}
          for name, fname, vid in [
              ("Storyboard Sketch",       "StoryboardSketch-Flux.safetensors",     869189),
              ("Storyboarding v2.0",      "Storyboarding-v2-Flux.safetensors",    1849823),
              ("Sketchy (Illustrious)",   "Sketchy-Illustrious.safetensors",      1452793),
              ("Film Noir v1.0",          "FilmNoir-v1-Flux.safetensors",          863747),
              ("Film Noir V1",            "FilmNoir-V1-Flux.safetensors",         1816859),
              ("Classic + Neo Film Noir", "ClassicNeoFilmNoir-Flux.safetensors",  1307068),
              ("Cinematic 1940s",         "Cinematic1940s-Flux.safetensors",      1527024),
              ("Cinematic Style v4",      "CinematicStyle-v4-Flux.safetensors",   1850943),
              ("Wong Kar-wai",            "WongKarwai-Cinematic-Flux.safetensors",  747253),
              ("Cinematic Film Stock",    "CinematicFilmStock-Flux.safetensors",  1408148),
              ("Retro Cinematic",         "RetroCinematic-Flux.safetensors",      1246680),
          ]],
    ]

# ─── DOWNLOAD ENGINE ──────────────────────────────────────────────────────────

def file_size(path):
    try: return path.stat().st_size
    except FileNotFoundError: return 0

def is_complete(entry):
    dest = MODELS / entry["dest"]
    if not dest.exists(): return False
    if entry["size"] == 0: return dest.stat().st_size > 0
    return dest.stat().st_size >= entry["size"]

def download(entry, idx, total, stats, dry_run=False):
    dest = MODELS / entry["dest"]
    name = entry["name"]
    url  = entry["url"]
    auth = entry.get("auth")
    expected = entry["size"]

    if is_complete(entry):
        return "skip"

    size_str = f" ({fmt_size(expected)})" if expected > 0 else ""
    print(f"  ↓  [{idx:2d}/{total}]  {name}{size_str}")

    if dry_run:
        return "dry"

    dest.parent.mkdir(parents=True, exist_ok=True)
    start_bytes = file_size(dest)
    start_time  = time.time()
    last_report = start_time

    cmd = ["wget", "-c", "-q", "--show-progress", "-O", str(dest), url]
    if auth:
        cmd = ["wget", "-c", "-q", "--show-progress",
               f"--header=Authorization: Bearer {auth}",
               "-O", str(dest), url]

    for attempt in range(1, 4):
        proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)

        while proc.poll() is None:
            time.sleep(10)
            now = time.time()
            if now - last_report >= 30:
                cur = file_size(dest)
                elapsed = now - start_time
                delta = cur - start_bytes
                if elapsed > 0 and delta > 0:
                    rate = delta / elapsed
                    remaining = (expected - cur) if expected > 0 else 0
                    eta = fmt_eta(remaining / rate) if rate > 0 and remaining > 0 else "?"
                    pct = f"{cur/expected*100:.0f}%" if expected > 0 else fmt_size(cur)
                    print(f"       {pct}  {fmt_rate(rate)}  ETA {eta}  "
                          f"[overall: {fmt_size(stats['done'])}/{fmt_size(stats['total'])}  "
                          f"~{fmt_eta(stats['eta']())}]")
                last_report = now

        if is_complete(entry):
            elapsed = time.time() - start_time
            delta = file_size(dest) - start_bytes
            rate = delta / elapsed if elapsed > 0 else 0
            stats["done"] += file_size(dest) - start_bytes if start_bytes == 0 else file_size(dest)
            print(f"       ✓  {fmt_size(file_size(dest))}  {fmt_eta(elapsed)}  {fmt_rate(rate)}")
            return "ok"

        if attempt < 3:
            print(f"       ✗  attempt {attempt} failed, retrying in 5s...")
            time.sleep(5)

    msg = f"FAILED after 3 attempts: {name} → {dest}"
    print(f"       ✗  FAILED (see {LOG.name})")
    with open(LOG, "a") as f:
        f.write(f"{msg}\n  url: {url}\n\n")
    return "fail"

# ─── DISK CHECK ───────────────────────────────────────────────────────────────

def check_disk(needed_bytes):
    stat = shutil.disk_usage(MODELS)
    free = stat.free
    if free < needed_bytes * 1.05:
        print(f"\n  ✗  Insufficient disk space.")
        print(f"     Needed:    {fmt_size(needed_bytes)}")
        print(f"     Available: {fmt_size(free)}")
        sys.exit(1)
    print(f"  Disk: {fmt_size(free)} free, {fmt_size(needed_bytes)} needed — OK")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def get_token(env_var, path):
    val = os.environ.get(env_var)
    if val: return val
    p = Path(path).expanduser()
    if p.exists(): return p.read_text().strip()
    return ""

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", "--dry-run", action="store_true",
                        help="Show what's missing and disk needed, then exit")
    parser.add_argument("--only", metavar="SECTION",
                        help="Only download this section (e.g. loras, wan, flux)")
    parser.add_argument("--skip", metavar="SECTION",
                        help="Skip this section")
    args = parser.parse_args()

    hf_token = get_token("HF_TOKEN", "~/.cache/huggingface/token")
    cv_token = get_token("CIVITAI_API_KEY", "~/.civitai_token")

    if not hf_token:
        print("  ⚠  No HuggingFace token found. Set HF_TOKEN or put token in "
              "~/.cache/huggingface/token")
    if not cv_token:
        print("  ⚠  No CivitAI token found. Set CIVITAI_API_KEY or put token in "
              "~/.civitai_token. CivitAI downloads will fail.")

    items = catalog(hf_token, cv_token)

    if args.only:
        items = [i for i in items if i["section"] == args.only]
        if not items:
            print(f"Unknown section '{args.only}'. "
                  f"Valid: {sorted({i['section'] for i in catalog('','')})}")
            sys.exit(1)
    if args.skip:
        items = [i for i in items if i["section"] != args.skip]

    missing  = [i for i in items if not is_complete(i)]
    skipping = [i for i in items if is_complete(i)]
    needed   = sum(i["size"] for i in missing if i["size"] > 0)

    print(f"\n  image_gen model installer")
    print(f"  {'─'*52}")
    print(f"  Total catalog : {len(items)} files")
    print(f"  Already done  : {len(skipping)} files")
    print(f"  To download   : {len(missing)} files  (~{fmt_size(needed)})")

    if not missing:
        print("\n  Everything is already installed.\n")
        return

    print()
    for sec in dict.fromkeys(i["section"] for i in missing):
        sec_items = [i for i in missing if i["section"] == sec]
        sz = sum(i["size"] for i in sec_items if i["size"] > 0)
        print(f"  {sec:<16} {len(sec_items):2d} files  {fmt_size(sz)}")
    print()

    if args.check:
        check_disk(needed)
        return

    check_disk(needed)
    print()

    # Rolling ETA: recompute every download
    session_start = time.time()
    session_downloaded = 0

    def overall_eta():
        elapsed = time.time() - session_start
        if elapsed < 10 or session_downloaded == 0:
            return -1
        rate = session_downloaded / elapsed
        remaining = sum(
            max(0, (i["size"] - file_size(MODELS / i["dest"])))
            for i in missing if i["size"] > 0
        )
        return remaining / rate if rate > 0 else -1

    stats = {"done": session_downloaded, "total": needed, "eta": overall_eta}

    ok = fail = skip = 0
    for idx, entry in enumerate(missing, 1):
        before = file_size(MODELS / entry["dest"])
        result = download(entry, idx, len(missing), stats, dry_run=args.check)
        after  = file_size(MODELS / entry["dest"])
        session_downloaded += max(0, after - before)
        stats["done"] = session_downloaded
        if result == "ok":   ok += 1
        elif result == "fail": fail += 1
        elif result == "skip": skip += 1

    print(f"\n  {'─'*52}")
    print(f"  Done: {ok}  Failed: {fail}  Skipped: {skip}")
    if fail:
        print(f"  See {LOG} for details on failures.")
    print()

if __name__ == "__main__":
    main()
