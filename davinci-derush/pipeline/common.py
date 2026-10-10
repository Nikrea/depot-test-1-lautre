"""Outils partagés par tous les scripts du pipeline de dérush."""
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from fractions import Fraction
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".mxf", ".mkv", ".avi", ".m4v", ".mts", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".aif", ".aiff"}

# Mots outils ignorés quand on cherche les mots-clés d'une phrase.
STOPWORDS = set("""
a au aux avec ce ces cet cette ceci cela ca c d dans de des du elle elles en et est etait
etre eux il ils j je l la le les leur leurs lui m ma mais me meme mes moi mon n ne nos notre
nous on ou par pas plus pour qu que qui s sa se ses si son sur t ta te tes toi ton tu un une
vos votre vous y ont a ai as avait avez avons sont suis es etes fait faire tout tous toute
toutes tres bien alors donc voila comme quand aussi encore deja ici la-bas puis apres avant
cest quil quelle dun dune lui sans sous entre vers chez rien jamais toujours peut
euh heu hum bon ben bah ouais oui non
""".split())


def need(tool):
    if shutil.which(tool) is None:
        sys.exit(f"[ERREUR] '{tool}' introuvable dans le PATH. "
                 "Installe FFmpeg : winget install Gyan.FFmpeg (puis rouvre le terminal).")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def probe(path):
    """Durée, cadence, taille et pistes d'un média (via ffprobe)."""
    path = Path(path)
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe n'arrive pas à lire {path} : {res.stderr.strip()}")
    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    is_image = path.suffix.lower() in IMAGE_EXT
    fps = None
    if v is not None and not is_image:
        for key in ("r_frame_rate", "avg_frame_rate"):
            rate = v.get(key)
            if rate and rate != "0/0":
                fps = float(Fraction(rate))
                break
    duration = 0.0
    if not is_image:
        duration = float(data.get("format", {}).get("duration")
                         or (v or a or {}).get("duration") or 0.0)
    return {
        "duration": duration,
        "fps": fps,
        "width": int(v["width"]) if v else None,
        "height": int(v["height"]) if v else None,
        "has_video": v is not None,
        "has_audio": a is not None,
        "audio_channels": int(a.get("channels", 2)) if a else 0,
        "audio_rate": int(a.get("sample_rate", 48000)) if a else 0,
        "is_image": is_image,
    }


def strip_accents(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def norm_word(word):
    """Forme comparable d'un mot : minuscules, sans accents ni ponctuation."""
    return re.sub(r"[^a-z0-9]+", "", strip_accents(word))


def tokens(text):
    """Mots significatifs d'un texte (pour la recherche par mots-clés)."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # camelCase -> camel Case
    out = []
    for tok in re.split(r"[^a-z0-9]+", strip_accents(text)):
        if len(tok) < 3 or tok in STOPWORDS or tok.isdigit() and len(tok) != 4:
            continue  # on garde les années (4 chiffres), pas les numéros de rush
        if re.fullmatch(r"[a-z]{1,3}\d+", tok):
            continue  # C0042, DSC1234, IMG...
        out.append(tok)
    return out


def stem(tok):
    """Racine grossière : 'voitures' et 'voiture' -> 'voitur'."""
    if len(tok) > 4 and tok[-1] in "sx":
        tok = tok[:-1]
    return tok[:6]


def tc(seconds):
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"


def tc_frames(frames, fps):
    fps_i = round(fps)
    f = frames % fps_i
    s = frames // fps_i
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


def project_paths(project_dir):
    """Arborescence standard d'un projet (voir README)."""
    root = Path(project_dir).resolve()
    work = root / "_derush"
    return {
        "root": root,
        "voix": root / "voix",
        "broll": root / "broll",
        "script": root / "script.txt",
        "work": work,
        "transcript": work / "transcript.json",
        "transcript_txt": work / "transcript_mots.txt",
        "decisions": work / "decisions.json",
        "edl": work / "edl.json",
        "rapport": work / "derush_rapport.md",
        "montage_txt": work / "montage_texte.txt",
        "index": work / "broll_index.json",
        "thumbs": work / "thumbs",
        "placements": work / "placements.json",
        "placements_md": work / "placements_rapport.md",
        "fcpxml": work / "timeline.fcpxml",
    }


def find_voice_file(voix_dir):
    voix_dir = Path(voix_dir)
    if not voix_dir.is_dir():
        sys.exit(f"[ERREUR] Dossier introuvable : {voix_dir}")
    files = sorted(p for p in voix_dir.iterdir()
                   if p.suffix.lower() in AUDIO_EXT | VIDEO_EXT)
    if not files:
        sys.exit(f"[ERREUR] Aucun fichier audio/vidéo dans {voix_dir}")
    if len(files) > 1:
        sys.exit("[ERREUR] Un seul fichier de voix par projet. Trouvés : "
                 + ", ".join(p.name for p in files)
                 + "\nFusionne-les ou garde uniquement la prise à monter.")
    return files[0]
