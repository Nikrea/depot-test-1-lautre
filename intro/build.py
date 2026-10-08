"""Construit l'intro complète : formes -> son -> images -> vidéo.

  python3 intro/build.py                 # 1080p, 24 i/s
  python3 intro/build.py --res 2160      # 4K
  python3 intro/build.py --fps 25        # autre cadence (PAL, 30, 60...)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import assets  # noqa: E402

OUT = os.path.join(assets.ROOT, "output")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--crf", type=int, default=None, help="qualité x264 (plus bas = meilleur)")
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()

    assets.load(rebuild=True)
    subprocess.run([sys.executable, os.path.join(HERE, "audio.py")], check=True)

    frames = os.path.join(OUT, f"frames_{a.res}")
    shutil.rmtree(frames, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"), "--res", str(a.res), "--fps", str(a.fps),
                    "--out", frames], check=True)

    label = "4K" if a.res == 2160 else f"{a.res}p"
    suffix = "" if a.fps == 24 else f"_{a.fps:g}fps"
    out = os.path.join(OUT, f"LAUTRE_intro_{label}{suffix}.mp4")
    crf = a.crf if a.crf is not None else (23 if a.res >= 2160 else 19)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", f"{a.fps:g}", "-i", os.path.join(frames, "%04d.png"),
        "-i", os.path.join(OUT, "intro_audio.wav"),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-tune", "film", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", out,
    ], check=True)
    if not a.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    print("vidéo :", out)


if __name__ == "__main__":
    main()
