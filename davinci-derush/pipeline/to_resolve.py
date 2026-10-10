"""Étape 5 : construit la timeline directement dans DaVinci Resolve Studio.

    python pipeline/to_resolve.py D:/Projets/MaVideo

Pré-requis : Resolve Studio OUVERT, Préférences > Système > Général >
"External scripting using" = Local, variables d'environnement posées
(setup_windows.ps1 s'en charge).

Crée un NOUVEAU projet (rien n'est touché dans tes projets existants) avec :
  V1/A1 : la voix dérushée     V2 : les B-rolls (sans leur son)
  marqueurs bleus : pourquoi chaque B-roll est là
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, project_paths, resolve_env_defaults  # noqa: E402


def connect():
    resolve_env_defaults()
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        api = os.environ.get("RESOLVE_SCRIPT_API")
        if api:
            sys.path.append(os.path.join(api, "Modules"))
        try:
            import DaVinciResolveScript as dvr
        except ImportError:
            sys.exit("[ERREUR] Module DaVinciResolveScript introuvable. Lance setup_windows.ps1 "
                     "puis rouvre le terminal.")
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        sys.exit("[ERREUR] Resolve ne répond pas. Vérifie qu'il est ouvert (version Studio) et que "
                 "Préférences > Système > Général > External scripting using = Local.")
    return resolve


def clip_fps(item, default):
    try:
        return float(item.GetClipProperty("FPS")) or default
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--nom", help="nom du projet Resolve (défaut : nom du dossier + date)")
    ap.add_argument("--resolution", default="1920x1080")
    ap.add_argument("--no-broll", action="store_true", help="seulement la voix dérushée")
    ap.add_argument("--no-markers", action="store_true")
    args = ap.parse_args()

    paths = project_paths(args.projet)
    edl = load_json(paths["edl"])
    fps = edl["fps"]
    placements = []
    clips = {}
    if not args.no_broll and paths["placements"].exists():
        placements = load_json(paths["placements"])["placements"]
        clips = {c["id"]: c for c in load_json(paths["index"])["clips"]}

    resolve = connect()
    print(f"[OK] Connecté à {resolve.GetProductName()} {resolve.GetVersionString()}")
    pm = resolve.GetProjectManager()
    name = args.nom or f"{paths['root'].name} - derush {datetime.datetime.now():%Y-%m-%d %Hh%M}"
    project = pm.CreateProject(name)
    if not project:
        sys.exit(f"[ERREUR] Impossible de créer le projet « {name} » (nom déjà pris ?). Utilise --nom.")
    w, h = args.resolution.lower().split("x")
    for key, val in (("timelineFrameRate", f"{fps:g}"), ("timelinePlaybackFrameRate", f"{fps:g}"),
                     ("timelineResolutionWidth", w), ("timelineResolutionHeight", h)):
        if not project.SetSetting(key, val):
            print(f"[!!] Réglage refusé : {key} = {val}")
    print(f"[OK] Projet « {name} » à {project.GetSetting('timelineFrameRate')} i/s")

    mp = project.GetMediaPool()
    root = mp.GetRootFolder()

    def import_into(folder_name, files):
        folder = mp.AddSubFolder(root, folder_name) or root
        mp.SetCurrentFolder(folder)
        items = mp.ImportMedia([str(f) for f in files]) or []
        found = {}
        for it in items:
            found[os.path.normcase(os.path.abspath(it.GetClipProperty("File Path")))] = it
        return found

    voice = import_into("VOIX", [edl["source"]])
    if not voice:
        sys.exit(f"[ERREUR] Import impossible : {edl['source']}")
    voice_item = next(iter(voice.values()))
    used = sorted({clips[p["broll"]]["path"] for p in placements if p["broll"] in clips})
    broll = import_into("BROLL", used) if used else {}
    print(f"[OK] Médias importés : 1 voix, {len(broll)} B-rolls")

    timeline = mp.CreateEmptyTimeline(f"{paths['root'].name} - derush")
    project.SetCurrentTimeline(timeline)
    if placements:
        timeline.AddTrack("video")
    t0 = timeline.GetStartFrame()

    # --- V1/A1 : la voix ---------------------------------------------------
    # La doc de l'API ne précise pas si endFrame est inclus : on le mesure sur le
    # premier morceau et on corrige si besoin.
    vfps = clip_fps(voice_item, fps)
    ratio = vfps / fps
    segs = edl["segments"]

    def voice_info(s, inclusive):
        a, b = round(s["src_in"] * ratio), round(s["src_out"] * ratio)
        return {"mediaPoolItem": voice_item, "startFrame": a, "endFrame": b - 1 if inclusive else b,
                "trackIndex": 1, "recordFrame": t0 + s["rec_in"]}

    inclusive = True
    first = mp.AppendToTimeline([voice_info(segs[0], True)]) or []
    if first:
        got, want = first[0].GetDuration(), segs[0]["src_out"] - segs[0]["src_in"]
        if got == want - 1:
            inclusive = False
            timeline.DeleteClips(first, False)
            first = mp.AppendToTimeline([voice_info(segs[0], False)]) or []
        elif got != want:
            print(f"[!!] Durée inattendue sur le 1er morceau : {got} au lieu de {want} images")
    rest = mp.AppendToTimeline([voice_info(s, inclusive) for s in segs[1:]]) or []
    print(f"[OK] Voix posée : {len(segs)} morceaux ({len(first) + len(rest)} éléments de timeline)")

    # --- V2 : les B-rolls -----------------------------------------------------
    infos, notes = [], []
    for p in placements:
        c = clips.get(p["broll"])
        item = c and broll.get(os.path.normcase(os.path.abspath(c["path"])))
        if not item:
            print(f"[!!] B-roll introuvable dans le Media Pool : {p['broll']}")
            continue
        length = p["rec_out"] - p["rec_in"]
        if c["type"] == "image":
            a, n = 0, length
        else:
            cf = clip_fps(item, fps)
            a, n = round(p["src_in_s"] * cf), max(1, round(length / fps * cf))
        infos.append({"mediaPoolItem": item, "startFrame": a, "endFrame": a + n - (1 if inclusive else 0),
                      "trackIndex": 2, "recordFrame": t0 + p["rec_in"], "mediaType": 1})
        notes.append(p)
    placed = mp.AppendToTimeline(infos) or [] if infos else []
    if infos:
        print(f"[OK] B-rolls posés : {len(placed)}/{len(infos)}")
        if len(placed) < len(infos):
            print("[!!] Certains B-rolls n'ont pas été posés (clip trop court ? photo plus courte que "
                  "la « durée standard des images fixes » dans les préférences ?)")

    if not args.no_markers:
        for p in notes:
            timeline.AddMarker(p["rec_in"], "Blue", p["broll"], f"{p.get('why', '')} ({p.get('phrase', '')})", 1)

    pm.SaveProject()
    resolve.OpenPage("edit")
    print(f"[OK] Terminé. Timeline « {timeline.GetName()} » ouverte dans la page Montage.")


if __name__ == "__main__":
    main()
