"""Étape 4 : premier jet du placement des B-rolls sur le texte monté.

    python pipeline/match_broll.py D:/Projets/MaVideo

Associe chaque phrase aux B-rolls dont le nom, les tags ou la description partagent
des mots avec elle. C'est un brouillon par mots-clés : Claude peut ensuite réécrire
_derush/placements.json en choisissant par le SENS (voir CLAUDE.md).

Format de placements.json (temps de la timeline en images, début = 0) :
    {"fps": 24, "placements": [
        {"broll": "B003", "rec_in": 120, "rec_out": 216, "src_in_s": 1.0,
         "phrase": "P004", "why": "Titanic"}]}
"""
import argparse
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, project_paths, save_json, stem, tc, tokens  # noqa: E402


def clip_terms(c):
    text = " ".join([c["name"], c.get("description", ""), " ".join(c.get("tags", []))])
    return {stem(t) for t in tokens(text)} | {stem(t) for t in c.get("keywords", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--min-len", type=float, default=2.0, help="durée mini d'un B-roll (s)")
    ap.add_argument("--max-len", type=float, default=6.0, help="durée maxi d'un B-roll (s)")
    ap.add_argument("--lead", type=float, default=0.25,
                    help="le B-roll arrive ce temps avant le mot qui l'appelle (s)")
    ap.add_argument("--force", action="store_true", help="écraser un placements.json existant")
    args = ap.parse_args()

    paths = project_paths(args.projet)
    if paths["placements"].exists() and not args.force:
        print(f"[OK] {paths['placements']} existe déjà (peut-être retouché par Claude). "
              "--force pour le régénérer.")
        return
    edl = load_json(paths["edl"])
    clips = load_json(paths["index"])["clips"]
    fps = edl["fps"]
    total = edl["duration_frames"] / fps
    terms = {c["id"]: clip_terms(c) for c in clips}
    by_id = {c["id"]: c for c in clips}

    # Un mot présent dans beaucoup de clips compte moins (pondération IDF).
    df = Counter(t for ts in terms.values() for t in ts)
    idf = {t: math.log(1 + len(clips) / df[t]) for t in df}

    placements, uses, busy_until = [], Counter(), 0.0
    for ph in edl["phrases"]:
        hits = {}
        for w in ph["words"]:
            for t in tokens(w["w"]):
                hits.setdefault(stem(t), (w["t"], t))
        best = None
        for cid, ts in terms.items():
            common = [t for t in hits if t in ts]
            if not common:
                continue
            score = sum(idf[t] for t in common) * 0.5 ** uses[cid]
            if best is None or score > best[0]:
                best = (score, cid, min(hits[t][0] for t in common), [hits[t][1] for t in common])
        if best is None:
            continue
        _, cid, anchor, common = best
        c = by_id[cid]
        rec_in = max(anchor - args.lead, ph["t_in"], busy_until)
        length = min(max(ph["t_out"] - rec_in + 0.5, args.min_len), args.max_len, total - rec_in)
        src_in = 0.0
        if c["type"] == "video":
            if c["duration"] >= length + 2:
                src_in = 1.0  # on évite la première seconde, souvent bougée
            elif c["duration"] > length:
                src_in = (c["duration"] - length) / 2
            length = min(length, c["duration"] - src_in)
        if length < args.min_len * 0.75:
            continue
        rin, rout = round(rec_in * fps), round((rec_in + length) * fps)
        placements.append({"broll": cid, "rec_in": rin, "rec_out": rout, "src_in_s": round(src_in, 3),
                           "phrase": ph["id"], "why": ", ".join(common)})
        uses[cid] += 1
        busy_until = rout / fps

    save_json(paths["placements"], {"fps": fps, "placements": placements})
    with open(paths["placements_md"], "w", encoding="utf-8") as f:
        f.write("# Placement des B-rolls\n\n| Timeline | Durée | Clip | Phrase | Pourquoi |\n|---|---|---|---|---|\n")
        texts = {p["id"]: p["text"] for p in edl["phrases"]}
        for p in placements:
            f.write(f"| {tc(p['rec_in'] / fps)} | {(p['rec_out'] - p['rec_in']) / fps:.1f} s | "
                    f"{p['broll']} `{by_id[p['broll']]['name']}` | {texts[p['phrase']][:80]} | {p['why']} |\n")
        unused = [c["name"] for c in clips if c["id"] not in uses]
        if unused:
            f.write(f"\n**Non utilisés ({len(unused)})** : " + ", ".join(unused) + "\n")
    covered = sum(p["rec_out"] - p["rec_in"] for p in placements) / fps
    print(f"[OK] {len(placements)} B-rolls placés, {100 * covered / max(total, 0.01):.0f} % de la durée couverte")
    print(f"[OK] {paths['placements']}\n[OK] {paths['placements_md']}")


if __name__ == "__main__":
    main()
