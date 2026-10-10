"""Étape 2 : dérush de la voix — enlève les blancs, les "euh" et les prises ratées.

    python pipeline/derush.py D:/Projets/MaVideo

Entrées  : _derush/transcript.json (+ _derush/decisions.json facultatif)
Sorties  : _derush/edl.json            liste des morceaux gardés (en images)
           _derush/derush_rapport.md   tout ce qui a été coupé, pour vérifier
           _derush/montage_texte.txt   le texte monté, phrase par phrase, avec timecodes

decisions.json (écrit à la main ou par Claude) a la priorité sur l'automatique :
    {"remove": [[120, 135, "reprise"]], "keep": [[300, 305]]}
Les numéros sont ceux de transcript_mots.txt, bornes incluses.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (load_json, need, norm_word, project_paths, save_json,  # noqa: E402
                    tc, tc_frames)

FILLERS = {"euh", "euhh", "heu", "hum", "hmm", "hmmm", "mmh", "mh", "em", "emm", "eum"}
# Doublons voulus qu'il ne faut pas traiter comme un bégaiement.
INTENTIONAL_DOUBLES = {"tres", "trop", "non", "oui", "si", "bien", "vite", "jamais", "plus"}


def detect_silences(media, noise_db, min_dur):
    """Plages de silence réelles mesurées par ffmpeg (sert à placer les coupes au propre)."""
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-vn",
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    sil, start = [], None
    for line in res.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            sil.append((start, float(m.group(1))))
            start = None
    if start is not None:
        sil.append((start, float("inf")))
    return sil


def detect_retakes(words, norm, min_match, min_pause, max_back_words, max_back_sec):
    """Repère les reprises : une suite d'au moins `min_match` mots redite après une pause.
    On garde la DERNIÈRE prise, on coupe la tentative précédente.
    Renvoie des couples (début de la tentative ratée, début de la reprise)."""
    found = []
    n = len(words)
    j = 1
    while j < n:
        pause = words[j]["start"] - words[j - 1]["end"]
        best = None
        if pause >= min_pause:
            for i in range(max(0, j - max_back_words), j):
                if words[j]["start"] - words[i]["start"] > max_back_sec:
                    continue
                m = 0
                while j + m < n and i + m < j and norm[i + m] and norm[i + m] == norm[j + m]:
                    m += 1
                if m >= min_match and (best is None or m > best[1]):
                    best = (i, m)
        if best:
            found.append((best[0], j))
            j += best[1]
        else:
            j += 1
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--fps", type=float, default=24.0, help="cadence de la timeline")
    ap.add_argument("--max-pause", type=float, default=0.35,
                    help="un blanc plus long que ça (s) est raccourci")
    ap.add_argument("--pad-before", type=float, default=0.10, help="air gardé avant la parole (s)")
    ap.add_argument("--pad-after", type=float, default=0.15, help="air gardé après la parole (s)")
    ap.add_argument("--pad-phrase", type=float, default=0.30,
                    help="air gardé après une fin de phrase (. ! ?) pour le rythme (s)")
    ap.add_argument("--noise-db", type=float, default=-38, help="seuil de silence (dB)")
    ap.add_argument("--retake-min-words", type=int, default=3)
    ap.add_argument("--no-retakes", action="store_true", help="ne pas couper les reprises automatiquement")
    ap.add_argument("--keep-fillers", action="store_true", help="garder les 'euh'")
    args = ap.parse_args()

    need("ffmpeg")
    paths = project_paths(args.projet)
    tr = load_json(paths["transcript"])
    words, fps = tr["words"], args.fps
    dur = tr["duration"]
    n = len(words)
    norm = [norm_word(w["w"]) for w in words]

    reason = [None] * n  # None = gardé

    def cut(a, b, why):
        for k in range(max(0, a), min(n - 1, b) + 1):
            if reason[k] is None:
                reason[k] = why

    if not args.keep_fillers:
        for k in range(n):
            if norm[k] in FILLERS:
                cut(k, k, "hésitation")
    for k in range(n - 1):  # bégaiement : "le le Titanic"
        if (norm[k] and norm[k] == norm[k + 1] and norm[k] not in INTENTIONAL_DOUBLES
                and words[k + 1]["start"] - words[k]["end"] < 0.6):
            cut(k, k, "bégaiement")
    if not args.no_retakes:
        # On compare sans les "euh", qui cassent souvent la répétition.
        idx = [k for k in range(n) if norm[k] and norm[k] not in FILLERS]
        for a, j in detect_retakes([words[k] for k in idx], [norm[k] for k in idx],
                                   args.retake_min_words, 0.25, 60, 30):
            cut(idx[a], idx[j] - 1, "reprise (auto)")

    if paths["decisions"].exists():
        dec = load_json(paths["decisions"])
        for r in dec.get("remove", []):
            a, b = int(r[0]), int(r[1])
            for k in range(a, min(n - 1, b) + 1):
                reason[k] = r[2] if len(r) > 2 else "coupe manuelle"
        for r in dec.get("keep", []):
            for k in range(int(r[0]), min(n - 1, int(r[1])) + 1):
                reason[k] = None
        print(f"[OK] decisions.json appliqué ({len(dec.get('remove', []))} coupes, "
              f"{len(dec.get('keep', []))} restaurations)")

    silences = detect_silences(tr["source"], args.noise_db, 0.12)

    def speech_end(t):
        """Fin réelle de la parole : début du silence mesuré juste après le mot."""
        for s, e in silences:
            if t - 0.15 <= s <= t + 0.40:
                return s, e
        return t, None

    def speech_start(t):
        for s, e in reversed(silences):
            if t - 0.40 <= e <= t + 0.15:
                return e, s
        return t, None

    # Groupes de mots gardés consécutifs, coupés aux mots retirés et aux longs blancs.
    groups, cur = [], None
    for k in range(n):
        if reason[k] is not None:
            cur = None
            continue
        if cur is not None and words[k]["start"] - words[cur[1]]["end"] <= args.max_pause:
            cur[1] = k
        else:
            cur = [k, k]
            groups.append(cur)

    segments = []
    for a, b in groups:
        w_a, w_b = words[a], words[b]
        t0, sil_before = speech_start(w_a["start"])
        t1, sil_after = speech_end(w_b["end"])
        pad_after = args.pad_phrase if re.search(r"[.!?…]$", w_b["w"]) else args.pad_after
        start, end = t0 - args.pad_before, t1 + pad_after
        if sil_before is not None:
            start = max(start, sil_before)
        if sil_after is not None:
            end = min(end, sil_after)
        # Ne jamais déborder sur un mot voisin (surtout un mot coupé).
        start = max(start, words[a - 1]["end"] if a > 0 else 0.0, 0.0)
        end = min(end, words[b + 1]["start"] if b + 1 < n else dur, dur)
        start = min(start, w_a["start"])
        end = max(end, min(w_b["end"], dur))
        segments.append([round(start * fps), round(end * fps), a, b])

    merged = []
    for s in segments:
        if merged and s[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], s[1])
            merged[-1][3] = s[3]
        elif s[1] - s[0] >= 3:
            merged.append(s)

    edl_segs, phrases_words, rec = [], [], 0
    for src_in, src_out, a, b in merged:
        edl_segs.append({"src_in": src_in, "src_out": src_out, "rec_in": rec,
                         "rec_out": rec + src_out - src_in, "words": [a, b],
                         "text": " ".join(w["w"] for k, w in enumerate(words[a:b + 1], a)
                                          if reason[k] is None)})
        for k in range(a, b + 1):
            if reason[k] is None:
                w = words[k]
                off = rec / fps - src_in / fps
                phrases_words.append((k, w["w"], w["start"] + off, w["end"] + off))
        rec += src_out - src_in

    # Phrases du texte monté (servent au placement des B-rolls).
    phrases, buf = [], []
    for item in phrases_words:
        buf.append(item)
        if re.search(r"[.!?…]$", item[1]) or len(buf) >= 25:
            phrases.append(buf)
            buf = []
    if buf:
        phrases.append(buf)
    phrases = [{"id": f"P{i + 1:03d}", "t_in": round(p[0][2], 3), "t_out": round(p[-1][3], 3),
                "text": " ".join(x[1] for x in p),
                "words": [{"i": x[0], "w": x[1], "t": round(x[2], 3)} for x in p]}
               for i, p in enumerate(phrases)]

    removed, k = [], 0
    while k < n:
        if reason[k] is None:
            k += 1
            continue
        a = k
        while k + 1 < n and reason[k + 1] == reason[a]:
            k += 1
        removed.append({"words": [a, k], "reason": reason[a], "t": words[a]["start"],
                        "text": " ".join(w["w"] for w in words[a:k + 1])})
        k += 1

    save_json(paths["edl"], {"fps": fps, "source": tr["source"], "source_duration": dur,
                             "duration_frames": rec, "segments": edl_segs,
                             "phrases": phrases, "removed": removed})

    new_dur = rec / fps
    with open(paths["rapport"], "w", encoding="utf-8") as f:
        f.write(f"# Rapport de dérush\n\n- Durée brute : **{tc(dur)}**\n"
                f"- Durée montée : **{tc(new_dur)}** ({100 * (1 - new_dur / max(dur, 0.01)):.0f} % retiré)\n"
                f"- Morceaux gardés : {len(edl_segs)}\n- Coupes de texte : {len(removed)}\n\n"
                "## Texte coupé\n\n| Mots | Temps (rush) | Raison | Texte |\n|---|---|---|---|\n")
        for r in removed:
            f.write(f"| {r['words'][0]}–{r['words'][1]} | {tc(r['t'])} | {r['reason']} | {r['text']} |\n")
        f.write("\n> Une coupe auto est fausse ? Ajoute `{\"keep\": [[début, fin]]}` dans "
                "`_derush/decisions.json` puis relance derush.py.\n")
    with open(paths["montage_txt"], "w", encoding="utf-8") as f:
        f.write("# Texte monté — timecodes de la TIMELINE (début = 0)\n\n")
        for p in phrases:
            f.write(f"{p['id']} | {tc(p['t_in'])} → {tc(p['t_out'])} | {p['text']}\n")

    print(f"[OK] {tc(dur)} → {tc(new_dur)}  ({len(edl_segs)} morceaux, {len(removed)} coupes de texte)")
    print(f"[OK] Timeline : {tc_frames(rec, fps)} à {fps:g} i/s")
    print(f"[OK] {paths['edl']}\n[OK] {paths['rapport']}\n[OK] {paths['montage_txt']}")


if __name__ == "__main__":
    main()
