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

REPO   = Path(__file__).parent.parent
MODELS = REPO / "models"
LOG    = REPO / "install_models.log"

HF_BASE = "https://huggingface.co"
CV_BASE = "https://civitai.com/api/download/models"

# ─── FORMAT HELPERS ──────────────────────────────────────────────────────────

def fmt_size(b):
    if b >= 1_073_741_824: return f"{b/1_073_741_824:.1f}G"
    if b >= 1_048_576:     return f"{b/1_048_576:.0f}M"
    return f"{b/1024:.0f}K"

def fmt_eta(secs):
    if secs < 0:    return "?"
    if secs < 60:   return f"{secs:.0f}s"
    if secs < 3600: return f"{secs/60:.0f}m"
    h, m = int(secs // 3600), int((secs % 3600) // 60)
    return f"{h}h {m}m"

def fmt_rate(bps):
    if bps >= 1_048_576: return f"{bps/1_048_576:.1f} MB/s"
    return f"{bps/1024:.0f} KB/s"

# ─── CATALOG ─────────────────────────────────────────────────────────────────

def catalog(hf_token, cv_token):
    """Return the full ordered list of model entries to install."""

    def hf(section, name, dest, repo, file, size=0):
        return {"section": section, "name": name, "dest": dest, "size": size,
                "url": f"{HF_BASE}/{repo}/resolve/main/{file}", "auth": hf_token}

    def cv(section, name, dest, vid, size=0):
        return {"section": section, "name": name, "dest": dest, "size": size,
                "url": f"{CV_BASE}/{vid}?token={cv_token}"}

    def hf_shards(section, name_pfx, dest_dir, repo, repo_dir, tmpl, sizes):
        """Generate N sharded HuggingFace entries. tmpl uses {i} and {n} keys."""
        n = len(sizes)
        entries = []
        for i, sz in enumerate(sizes, 1):
            fname = tmpl.format(i=i, n=n)
            repo_path = f"{repo_dir}/{fname}" if repo_dir else fname
            entries.append(hf(section, f"{name_pfx} {i}/{n}",
                              f"{dest_dir}/{fname}", repo, repo_path, sz))
        return entries

    LLAVA_SIZES = [4_977_222_880, 4_999_802_616, 4_915_916_080, 1_100_000_000]
    WAN_SIZES   = [9_994_119_944, 9_943_979_184, 9_943_979_184,
                   9_839_059_744, 9_839_059_744, 7_595_559_224]
    SHARD_TMPL  = "diffusion_pytorch_model-{i:05d}-of-{n:05d}.safetensors"

    return [

        # ── Checkpoints ──────────────────────────────────────────────────────
        hf("checkpoints", "Illustrious XL v0.1",
           "checkpoints/Illustrious-XL-v0.1.safetensors",
           "OnomaAIResearch/Illustrious-xl-early-release-v0",
           "Illustrious-XL-v0.1.safetensors", 6_979_321_856),

        hf("checkpoints", "SVD-XT",
           "checkpoints/svd_xt.safetensors",
           "stabilityai/stable-video-diffusion-img2vid-xt",
           "svd_xt.safetensors", 9_559_625_980),

        # ── Flux ─────────────────────────────────────────────────────────────
        hf("flux", "Flux.1-dev",
           "diffusion_models/flux1-dev.safetensors",
           "black-forest-labs/FLUX.1-dev", "flux1-dev.safetensors", 23_804_823_040),

        hf("flux", "Flux.1-Canny-dev",
           "diffusion_models/flux1-canny-dev.safetensors",
           "black-forest-labs/FLUX.1-Canny-dev", "flux1-canny-dev.safetensors", 11_903_238_144),

        hf("flux", "Flux.1-Depth-dev",
           "diffusion_models/flux1-depth-dev.safetensors",
           "black-forest-labs/FLUX.1-Depth-dev", "flux1-depth-dev.safetensors", 11_903_238_144),

        hf("flux", "Flux.1-Kontext-dev",
           "diffusion_models/flux1-kontext-dev.safetensors",
           "black-forest-labs/FLUX.1-Kontext-dev", "flux1-kontext-dev.safetensors", 23_802_947_360),

        hf("flux", "Flux Redux",
           "style_models/flux1-redux-dev.safetensors",
           "black-forest-labs/FLUX.1-Redux-dev", "flux1-redux-dev.safetensors", 130_000_000),

        hf("flux", "SigCLIP Vision (Redux)",
           "clip_vision/sigclip_vision_patch14_384.safetensors",
           "Comfy-Org/sigclip_vision_384", "sigclip_vision_patch14_384.safetensors", 856_000_000),

        # ── VAE ──────────────────────────────────────────────────────────────
        hf("vae", "SDXL VAE fp16-fix",
           "vae/sdxl.vae.safetensors",
           "madebyollin/sdxl-vae-fp16-fix", "sdxl.vae.safetensors", 334_641_162),

        hf("vae", "Flux AE",
           "vae/flux-ae.safetensors",
           "black-forest-labs/FLUX.1-dev", "ae.safetensors", 334_643_202),

        # ── Text Encoders ─────────────────────────────────────────────────────
        hf("encoders", "CLIP-L (Flux)",
           "text_encoders/clip_l.safetensors",
           "comfyanonymous/flux_text_encoders", "clip_l.safetensors", 246_144_152),

        hf("encoders", "T5-XXL FP8 (Flux)",
           "text_encoders/t5xxl_fp8_e4m3fn.safetensors",
           "comfyanonymous/flux_text_encoders", "t5xxl_fp8_e4m3fn.safetensors", 4_891_624_992),

        # ── HunyuanVideo ─────────────────────────────────────────────────────
        hf("hunyuan", "HunyuanVideo transformer FP8",
           "diffusion_models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors",
           "Kijai/HunyuanVideo_comfy",
           "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors", 13_000_000_000),

        hf("hunyuan", "HunyuanVideo VAE",
           "vae/hunyuan/pytorch_model.pt",
           "tencent/HunyuanVideo", "hunyuan-video-t2v-720p/vae/pytorch_model.pt", 941_000_000),

        *hf_shards("hunyuan", "llava-llama-3-8b",
                   "text_encoders/llava-llama-3-8b",
                   "Kijai/llava-llama-3-8b-text-encoder-tokenizer", "",
                   "model-{i:05d}-of-{n:05d}.safetensors", LLAVA_SIZES),

        # ── WAN 2.2 I2V ──────────────────────────────────────────────────────
        *[shard
          for variant in ("high_noise", "low_noise")
          for shard in hf_shards(
              "wan", f"WAN 2.2 {variant}",
              f"diffusion_models/wan2.2-i2v/{variant}",
              "Wan-AI/Wan2.2-I2V-A14B", f"{variant}_model",
              SHARD_TMPL, WAN_SIZES)],

        hf("wan", "WAN 2.2 T5 encoder",
           "text_encoders/wan-umt5-xxl-enc-bf16.pth",
           "Wan-AI/Wan2.2-I2V-A14B", "models_t5_umt5-xxl-enc-bf16.pth", 11_361_920_418),

        hf("wan", "WAN 2.2 VAE",
           "vae/wan/Wan2.1_VAE.pth",
           "Wan-AI/Wan2.2-I2V-A14B", "Wan2.1_VAE.pth", 507_609_880),

        # ── ControlNet ────────────────────────────────────────────────────────
        hf("controlnet", "Flux Depth ControlNet v3 (XLabs)",
           "controlnet/flux-depth-controlnet-v3.safetensors",
           "XLabs-AI/flux-controlnet-depth-v3",
           "flux-depth-controlnet-v3.safetensors", 1_400_000_000),

        hf("controlnet", "Flux Canny ControlNet v3 (XLabs)",
           "controlnet/flux-canny-controlnet-v3.safetensors",
           "XLabs-AI/flux-controlnet-canny-v3",
           "flux-canny-controlnet-v3.safetensors", 1_400_000_000),

        hf("controlnet", "OpenPose XL2 (SDXL)",
           "controlnet/OpenPoseXL2.safetensors",
           "thibaud/controlnet-openpose-sdxl-1.0",
           "OpenPoseXL2.safetensors", 4_700_000_000),

        hf("controlnet", "ControlNet Union Pro (Shakker-Labs)",
           "controlnet/flux-controlnet-union-pro-shakker.safetensors",
           "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro",
           "diffusion_pytorch_model.safetensors", 6_603_953_920),

        hf("controlnet", "OpenPose ControlNet (Flux)",
           "controlnet/flux-openpose-controlnet.safetensors",
           "raulc0399/flux_dev_openpose_controlnet",
           "model.safetensors", 2_975_238_096),

        hf("controlnet", "ControlNet Union (InstantX)",
           "controlnet/flux-controlnet-union-instantx.safetensors",
           "InstantX/FLUX.1-dev-Controlnet-Union",
           "diffusion_pytorch_model.safetensors", 6_603_953_920),

        # ── Upscalers ─────────────────────────────────────────────────────────
        cv("upscalers", "4x-UltraSharp",
           "upscale_models/4x-UltraSharp.pth", 125843, 67_040_256),

        {"section": "upscalers", "name": "RealESRGAN x4plus",
         "dest": "upscale_models/RealESRGAN_x4plus.pth", "size": 67_040_256,
         "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"},

        hf("upscalers", "4x-AnimeSharp",
           "upscale_models/4x-AnimeSharp.pth",
           "f5aiteam/Upscaler_Models", "4x-AnimeSharp.pth", 67_040_256),

        # ── AnimateDiff ───────────────────────────────────────────────────────
        hf("animatediff", "AnimateDiff motion adapter v1.5-3",
           "animatediff_models/mm_sd_v15_v3.safetensors",
           "conrevo/AnimateDiff-A1111",
           "motion_module/mm_sd15_v3.safetensors", 1_600_000_000),

        *[hf("animatediff", f"AnimateDiff camera LoRA: {lname}",
             f"animatediff_motion_lora/{fname}",
             "Cseti/Basic_camera_motion_LoRAs_sd15-ad2-v1", fname, 118_000_000)
          for fname, lname in [
              ("1600_cseti_1077723_camera-zoomin-10vid_mv2.safetensors",  "ZoomIn"),
              ("1600_cseti_9192119_camera-zoomout-10vid_mv2.safetensors", "ZoomOut"),
              ("1600_cseti_9213319_camera-lateral_left-10vid_mv2.safetensors",  "PanLeft"),
              ("1600_cseti_6664682_camera-lateral_right-10vid_mv2.safetensors", "PanRight"),
              ("1600_cseti_1720230_camera-crane_up-10vid_mv2.safetensors",   "TiltUp"),
              ("1600_cseti_9406077_camera-crane_down-10vid_mv2.safetensors", "TiltDown"),
              ("2800_cseti_1093371_camera-zoomin-32f-10vid_mv2.safetensors", "ZoomIn-32f"),
          ]],

        # ── LoRAs (HuggingFace) ───────────────────────────────────────────────
        hf("loras", "Film Storyboard In-Context",
           "loras/film-storyboard.safetensors",
           "ali-vilab/In-Context-LoRA", "film-storyboard.safetensors", 180_000_000),

        hf("loras", "QWEN Next Scene v2",
           "loras/QwenNextScene-v2.safetensors",
           "lovis93/next-scene-qwen-image-lora-2509",
           "next-scene_lora-v2-3000.safetensors", 309_000_000),

        hf("loras", "XLabs IP-Adapter v2",
           "loras/flux-ip-adapter-v2-xlabs.safetensors",
           "XLabs-AI/flux-ip-adapter-v2", "ip_adapter.safetensors", 1_057_356_424),

        # ── LoRAs (CivitAI) ───────────────────────────────────────────────────
        *[cv("loras", name, f"loras/{fname}", vid)
          for name, fname, vid in [
              # Anime / Illustration / Cartoon / Graphic
              ("Anime CRABDM",        "Anime-CRABDM-Flux.safetensors",          1376386),   # Flux-specific ver
              ("Neurocore ShadowCircuit", "Neurocore-ShadowCircuit-Flux.safetensors", 1050932),  # Flux-only ver
              ("RetroAnime",          "RetroAnime-Flux.safetensors",            806265),
              ("FluxMyth SharpL1nes", "FluxMythSharpL1nes.safetensors",         675777),    # civitai/599757; verify identity
              ("Illustration Concept","IllustrationConcept-Flux.safetensors",   1619213),   # Flux ver 6
              ("Painterly Fantasy",   "PainterlyFantasy-Flux.safetensors",      1189379),
              ("Character Design V2", "CharacterDesign-FluxV2.safetensors",     765872),    # FluxV2 ver
              ("Disney Studios",      "Disney-Studios-Flux.safetensors",        738866),
              ("Comic Book Page",     "ComicBookPage-Flux.safetensors",         841525),    # Comic Strip F1D v1.5
              ("Swiss Design",        "SwissDesign-Flux.safetensors",           913310),
              ("Milton Glaser",       "MiltonGlaser-Flux.safetensors",          1003311),
              ("Graffiti Logo",       "GraffitiLogo-Flux.safetensors",          935989),
              ("Logo Maker 1024",     "LogoMaker1024-Flux.safetensors",         846937),
              # Storyboard / Noir / Cinematic
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

def _file_size(path):
    try: return path.stat().st_size
    except FileNotFoundError: return 0


def _is_complete(entry):
    dest = MODELS / entry["dest"]
    if not dest.exists(): return False
    sz = dest.stat().st_size
    return sz > 0 if entry["size"] == 0 else sz >= entry["size"]


def _wget_cmd(url, dest, auth):
    cmd = ["wget", "-c", "-q", "--show-progress", "-O", str(dest), url]
    if auth:
        cmd.insert(3, f"--header=Authorization: Bearer {auth}")
    return cmd


def _poll_progress(proc, dest, entry, stats, start_bytes, t0):
    """Drive proc to completion, printing progress every 30s."""
    last_report = t0
    while proc.poll() is None:
        time.sleep(10)
        now = time.time()
        if now - last_report < 30:
            continue
        cur, elapsed = _file_size(dest), now - t0
        delta = cur - start_bytes
        if elapsed > 0 and delta > 0:
            rate = delta / elapsed
            expected = entry["size"]
            remaining = max(0, expected - cur) if expected > 0 else 0
            eta = fmt_eta(remaining / rate) if remaining > 0 else "?"
            pct = f"{cur/expected*100:.0f}%" if expected > 0 else fmt_size(cur)
            print(f"       {pct}  {fmt_rate(rate)}  ETA {eta}  "
                  f"[overall: {fmt_size(stats['done'])}/{fmt_size(stats['total'])}  "
                  f"~{fmt_eta(stats['eta']())}]")
        last_report = now
    return time.time() - t0


def download(entry, idx, total, stats):
    dest = MODELS / entry["dest"]
    if _is_complete(entry):
        return "skip"

    expected = entry["size"]
    print(f"  ↓  [{idx:2d}/{total}]  {entry['name']}"
          + (f" ({fmt_size(expected)})" if expected > 0 else ""))

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = _wget_cmd(entry["url"], dest, entry.get("auth"))

    for attempt in range(1, 4):
        start_bytes = _file_size(dest)
        proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
        elapsed = _poll_progress(proc, dest, entry, stats, start_bytes, time.time())

        if _is_complete(entry):
            final = _file_size(dest)
            rate = (final - start_bytes) / elapsed if elapsed > 0 else 0
            print(f"       ✓  {fmt_size(final)}  {fmt_eta(elapsed)}  {fmt_rate(rate)}")
            return "ok"

        if attempt < 3:
            print(f"       ✗  attempt {attempt} failed, retrying in 5s...")
            time.sleep(5)

    print(f"       ✗  FAILED (see {LOG.name})")
    with open(LOG, "a") as f:
        f.write(f"FAILED after 3 attempts: {entry['name']} → {dest}\n"
                f"  url: {entry['url']}\n\n")
    return "fail"

# ─── DISK CHECK ──────────────────────────────────────────────────────────────

def check_disk(needed_bytes):
    free = shutil.disk_usage(MODELS).free
    if free < needed_bytes * 1.05:
        print(f"\n  ✗  Insufficient disk space.")
        print(f"     Needed:    {fmt_size(needed_bytes)}")
        print(f"     Available: {fmt_size(free)}")
        sys.exit(1)
    print(f"  Disk: {fmt_size(free)} free, {fmt_size(needed_bytes)} needed — OK")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def _get_token(env_var, path):
    val = os.environ.get(env_var)
    if val: return val
    p = Path(path).expanduser()
    return p.read_text().strip() if p.exists() else ""


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

    hf_token = _get_token("HF_TOKEN", "~/.cache/huggingface/token")
    cv_token = _get_token("CIVITAI_API_KEY", "~/.civitai_token")

    if not hf_token:
        print("  ⚠  No HuggingFace token. Set HF_TOKEN or ~/.cache/huggingface/token")
    if not cv_token:
        print("  ⚠  No CivitAI token. Set CIVITAI_API_KEY or ~/.civitai_token"
              " — CivitAI downloads will fail.")

    items = catalog(hf_token, cv_token)
    all_sections = sorted({i["section"] for i in items})

    if args.only:
        items = [i for i in items if i["section"] == args.only]
        if not items:
            print(f"Unknown section '{args.only}'. Valid: {all_sections}")
            sys.exit(1)
    if args.skip:
        items = [i for i in items if i["section"] != args.skip]

    missing = [i for i in items if not _is_complete(i)]
    needed  = sum(i["size"] for i in missing if i["size"] > 0)

    print(f"\n  image_gen model installer")
    print(f"  {'─'*52}")
    print(f"  Total catalog : {len(items)} files")
    print(f"  Already done  : {len(items) - len(missing)} files")
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

    check_disk(needed)

    if args.check:
        return

    print()
    t0 = time.time()
    stats = {"done": 0, "total": needed, "eta": None}

    def overall_eta():
        elapsed = time.time() - t0
        if elapsed < 10 or stats["done"] == 0:
            return -1
        rate = stats["done"] / elapsed
        remaining = sum(max(0, e["size"] - _file_size(MODELS / e["dest"]))
                        for e in missing if e["size"] > 0)
        return remaining / rate if rate > 0 else -1

    stats["eta"] = overall_eta

    ok = fail = skip = 0
    for idx, entry in enumerate(missing, 1):
        before = _file_size(MODELS / entry["dest"])
        result = download(entry, idx, len(missing), stats)
        stats["done"] += max(0, _file_size(MODELS / entry["dest"]) - before)
        if result == "ok":     ok += 1
        elif result == "fail": fail += 1
        elif result == "skip": skip += 1

    print(f"\n  {'─'*52}")
    print(f"  Done: {ok}  Failed: {fail}  Skipped: {skip}")
    if fail:
        print(f"  See {LOG} for details on failures.")
    print()


if __name__ == "__main__":
    main()
