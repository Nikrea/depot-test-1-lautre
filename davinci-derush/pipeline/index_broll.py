"""Étape 3 : inventaire des B-rolls (durée, cadence, mots-clés, planche d'images).

    python pipeline/index_broll.py D:/Projets/MaVideo

Sortie : _derush/broll_index.json + _derush/thumbs/Bxxx.jpg (3 images par clip).
Les champs "description" et "tags" sont à remplir en regardant les planches
(c'est le rôle de Claude, voir CLAUDE.md) : ils sont conservés si on relance.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (IMAGE_EXT, VIDEO_EXT, load_json, need, probe,  # noqa: E402
                    project_paths, save_json, tc, tokens)


def contact_sheet(media, info, out, width=480):
    """Planche de 3 images (début, milieu, fin) — ou la photo réduite."""
    out.parent.mkdir(parents=True, exist_ok=True)
    scale = f"scale={width}:-2"
    if info["is_image"]:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(media), "-vf", scale, "-frames:v", "1", str(out)]
        subprocess.run(cmd, check=True)
        return
    d = max(info["duration"], 0.1)
    inputs = []
    for t in (0.15 * d, 0.5 * d, 0.85 * d):
        inputs += ["-ss", f"{t:.3f}", "-i", str(media)]
    filt = ";".join(f"[{k}:v]{scale},setsar=1[v{k}]" for k in range(3)) + ";[v0][v1][v2]hstack=3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", filt,
                    "-frames:v", "1", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--force-thumbs", action="store_true", help="refaire les planches")
    args = ap.parse_args()

    need("ffmpeg")
    paths = project_paths(args.projet)
    if not paths["broll"].is_dir():
        sys.exit(f"[ERREUR] Dossier introuvable : {paths['broll']}")

    old = {}
    if paths["index"].exists():
        old = {c["path"]: c for c in load_json(paths["index"]).get("clips", [])}

    files = sorted(p for p in paths["broll"].rglob("*")
                   if p.is_file() and p.suffix.lower() in VIDEO_EXT | IMAGE_EXT
                   and not p.name.startswith("."))
    ignored = sorted(p.name for p in paths["broll"].rglob("*")
                     if p.is_file() and p.suffix.lower() in {".braw", ".r3d", ".ari"})
    if ignored:
        print(f"[!!] Formats RAW non lisibles par FFmpeg, ignorés : {', '.join(ignored)} "
              "(exporte une version proxy .mov/.mp4)")

    used_ids = {c["id"] for c in old.values()}
    next_id = max([int(i[1:]) for i in used_ids] + [0]) + 1
    clips = []
    for p in files:
        key = str(p.resolve())
        prev = old.get(key, {})
        try:
            info = probe(p)
        except RuntimeError as e:
            print(f"[!!] {e}")
            continue
        if not info["has_video"]:
            continue
        cid = prev.get("id")
        if not cid:
            cid = f"B{next_id:03d}"
            next_id += 1
        thumb = paths["thumbs"] / f"{cid}.jpg"
        if args.force_thumbs or not thumb.exists():
            try:
                contact_sheet(p, info, thumb)
            except subprocess.CalledProcessError:
                print(f"[!!] Planche impossible pour {p.name}")
        rel = p.relative_to(paths["broll"])
        clips.append({
            "id": cid, "path": key, "name": str(rel),
            "type": "image" if info["is_image"] else "video",
            "duration": round(info["duration"], 3), "fps": info["fps"],
            "width": info["width"], "height": info["height"],
            "keywords": sorted(set(tokens(" ".join(rel.with_suffix("").parts)))),
            "thumb": str(thumb.relative_to(paths["work"])).replace("\\", "/"),
            "description": prev.get("description", ""),
            "tags": prev.get("tags", []),
        })
        label = "photo" if info["is_image"] else f"{tc(info['duration'])} @ {info['fps']:.3f} i/s"
        print(f"  {cid}  {rel}  ({label})")

    save_json(paths["index"], {"broll_dir": str(paths["broll"]), "clips": clips})
    todo = sum(1 for c in clips if not c["description"])
    print(f"[OK] {len(clips)} B-rolls indexés → {paths['index']}")
    if todo:
        print(f"[..] {todo} clips sans description : demande à Claude de regarder _derush/thumbs/ "
              "et de remplir 'description' + 'tags' (le calage sera bien meilleur).")


if __name__ == "__main__":
    main()
