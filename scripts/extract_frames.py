#!/usr/bin/env python3
"""Pull picked frames out of a rendered clip into plates/ — the Burst method step.

The video drivers (video_shot.py, h3_t2v.py) render a clip; the Burst method takes
the frames you like from that clip as start frames / references for the next step
(see PRODUCTION_WORKFLOW.md). This is the tool that lands those frames in plates/.

Two verbs:

  browse — find your picks. Builds a contact sheet (every Nth frame), each thumbnail
           labelled with its frame index and timestamp, and opens it in the browser.
           Reads off the frame/second you want; saves nothing.

  save   — the default. Extracts the exact frames you name, at timestamps (--at) or
           frame indices (--frame), into plates/ (or --out), named <prefix>_NN.png.

Usage:
    extract_frames.py clip.mp4 --browse [--every N]
    extract_frames.py clip.mp4 --at 1.5 3.0 4.2 [--out plates/] [--prefix hero]
    extract_frames.py clip.mp4 --frame 24 72 [--prefix hero]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PLATES = REPO / "plates"

# Contact-sheet target: aim for about this many thumbnails across the whole clip
# when --every is not given. Enough to spot a good frame, few enough to scan.
CONTACT_THUMBS = 40


def probe(clip):
    """Return (fps, duration_seconds, total_frames) from ffprobe.

    Duration and frame rate are always present; total is derived from them because
    a container's nb_frames is often absent for the mp4/webm these drivers emit.
    """
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate:format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
        text=True,
    ).split()
    num, den = out[0].split("/")
    fps = float(num) / float(den)
    duration = float(out[1])
    return fps, duration, round(duration * fps)


def extract_at_time(clip, seconds, dst):
    """Accurate-seek a single frame at `seconds` to dst (decodes from start, exact)."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
         "-ss", f"{seconds}", "-frames:v", "1", str(dst)],
        check=True,
    )


def extract_at_frame(clip, index, dst):
    """Extract the exact frame at integer `index` to dst via the select filter."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
         "-vf", f"select=eq(n\\,{index})", "-frames:v", "1", "-vsync", "0", str(dst)],
        check=True,
    )


def browse(clip, fps, total, every):
    """Build a labelled contact sheet of every `every`-th frame and open it."""
    stage = Path(tempfile.mkdtemp(prefix="extract_frames_"))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
         "-vf", f"select=not(mod(n\\,{every})),scale=320:-1", "-vsync", "0",
         str(stage / "f_%05d.png")],
        check=True,
    )
    thumbs = sorted(stage.glob("f_*.png"))
    cards = []
    for k, thumb in enumerate(thumbs):
        frame = k * every
        t = frame / fps
        cards.append({"src": thumb.name,
                      "caption": f"frame <b>{frame}</b> · <b>{t:.2f}s</b>"})
    gallery.write_gallery(
        stage, f"Contact sheet · {clip.name} · every {every}f", cards,
        media="img", theme="dark",
        subtitle=f"{total} frames @ {fps:.3f}fps — read off a frame/second, then "
                 f"re-run with <code>--at</code> or <code>--frame</code>")
    print(f"[browse] {len(thumbs)} thumbnails from {total} frames (every {every})")
    gallery.serve_and_block(stage, keep=False)


def save(clip, fps, duration, total, times, frames, out_dir, prefix):
    """Extract each named time/frame into out_dir as <prefix>_NN.png, in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    picks = [("t", t) for t in times] + [("f", i) for i in frames]
    for seq, (kind, value) in enumerate(picks, start=1):
        dst = out_dir / f"{prefix}_{seq:02d}.png"
        if kind == "t":
            if not 0 <= value <= duration:
                sys.exit(f"--at {value}s is outside the clip (0–{duration:.2f}s)")
            extract_at_time(clip, value, dst)
            print(f"[{seq:02d}] {value:.2f}s -> {dst}")
        else:
            if not 0 <= value < total:
                sys.exit(f"--frame {value} is outside the clip (0–{total - 1})")
            extract_at_frame(clip, value, dst)
            print(f"[{seq:02d}] frame {value} ({value / fps:.2f}s) -> {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clip", help="rendered clip (mp4/webm) to pull frames from")
    ap.add_argument("--browse", action="store_true",
                    help="open a labelled contact sheet to find picks; saves nothing")
    ap.add_argument("--every", type=int, default=None,
                    help="contact-sheet stride in frames (default: ~40 thumbnails)")
    ap.add_argument("--at", type=float, nargs="+", default=[],
                    help="timestamps in seconds to extract")
    ap.add_argument("--frame", type=int, nargs="+", default=[],
                    help="frame indices to extract")
    ap.add_argument("--out", default=str(PLATES),
                    help="output directory for saved frames (default: plates/)")
    ap.add_argument("--prefix", default=None,
                    help="filename prefix for saved frames (default: clip stem)")
    args = ap.parse_args()

    clip = Path(args.clip).expanduser()
    if not clip.exists():
        sys.exit(f"no such clip: {clip}")
    fps, duration, total = probe(clip)

    if args.browse:
        every = args.every or max(1, total // CONTACT_THUMBS)
        browse(clip, fps, total, every)
        return

    if not args.at and not args.frame:
        sys.exit("nothing to save — pass --at SECONDS / --frame INDEX, or --browse "
                 "to find picks first")
    prefix = args.prefix or clip.stem
    save(clip, fps, duration, total, args.at, args.frame,
         Path(args.out).expanduser(), prefix)


if __name__ == "__main__":
    main()
