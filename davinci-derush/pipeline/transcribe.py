"""Étape 1 : transcription mot à mot (timecodes par mot) avec faster-whisper.

    python pipeline/transcribe.py D:/Projets/MaVideo
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import find_voice_file, need, probe, project_paths, save_json, tc  # noqa: E402

# Whisper "nettoie" volontiers les hésitations. Une consigne pleine de "euh" et de
# reprises l'incite à les écrire, ce qui permet ensuite de les couper.
FILLER_PROMPT = ("Euh, alors... hum, en fait, euh, je... je voulais dire, bon. "
                 "Euh, voilà, euh, on reprend.")


def load_audio(path, rate=16000):
    """Décode l'audio avec FFmpeg (évite les soucis de version de PyAV)."""
    import numpy as np
    res = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
                          "-f", "s16le", "-"], capture_output=True, check=True)
    return np.frombuffer(res.stdout, np.int16).astype(np.float32) / 32768.0


def add_cuda_dlls():
    """Sous Windows, rend visibles les DLL CUDA installées par pip (nvidia-cublas/cudnn)."""
    if os.name != "nt":
        return
    try:
        import nvidia
    except ImportError:
        return
    for base in nvidia.__path__:
        for sub in ("cublas", "cudnn"):
            dll_dir = os.path.join(base, sub, "bin")
            if os.path.isdir(dll_dir):
                os.add_dll_directory(dll_dir)
                os.environ["PATH"] = dll_dir + os.pathsep + os.environ["PATH"]


def pick_device(device):
    if device != "auto":
        return device
    try:
        import ctranslate2
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def run(WhisperModel, audio, args, device):
    compute = "float16" if device == "cuda" else "int8"
    print(f"[..] Modèle {args.model} sur {device} ({compute}) — premier lancement : téléchargement du modèle")
    model = WhisperModel(args.model, device=device, compute_type=compute)
    t0 = time.time()
    segments, info = model.transcribe(
        audio, language=args.lang, word_timestamps=True, beam_size=5,
        initial_prompt=FILLER_PROMPT, condition_on_previous_text=False,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 700})

    words, segs = [], []
    for seg in segments:
        first = len(words)
        for w in seg.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append({"i": len(words), "w": text, "start": round(w.start, 3),
                          "end": round(w.end, 3), "p": round(w.probability, 3)})
        if len(words) > first:
            segs.append({"start": words[first]["start"], "end": words[-1]["end"],
                         "words": [first, len(words) - 1], "text": seg.text.strip()})
        pct = 100 * seg.end / max(info.duration, 1)
        print(f"\r[..] {tc(seg.end)} / {tc(info.duration)}  ({pct:4.1f} %)", end="", flush=True)
    print(f"\n[OK] {len(words)} mots en {time.time() - t0:.0f} s")
    return words, segs, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet", help="dossier du projet (contient voix/ et broll/)")
    ap.add_argument("--model", default="large-v3",
                    help="large-v3 (précis), medium, small (rapide sur CPU)")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--device", default="auto", help="auto, cuda ou cpu")
    ap.add_argument("--force", action="store_true", help="refaire même si transcript.json existe")
    args = ap.parse_args()

    need("ffmpeg")
    need("ffprobe")
    paths = project_paths(args.projet)
    voice = find_voice_file(paths["voix"])
    if paths["transcript"].exists() and not args.force:
        print(f"[OK] Transcription déjà faite : {paths['transcript']} (--force pour refaire)")
        return

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("[ERREUR] faster-whisper manquant : pip install -r requirements.txt")

    info_media = probe(voice)
    audio = load_audio(voice)
    add_cuda_dlls()
    device = pick_device(args.device)
    try:
        words, segs, info = run(WhisperModel, audio, args, device)
    except Exception as e:
        if device != "cuda":
            raise
        print(f"\n[!!] Échec sur GPU ({e}) — on repasse sur le processeur.")
        words, segs, info = run(WhisperModel, audio, args, "cpu")

    save_json(paths["transcript"], {
        "source": str(voice), "duration": info_media["duration"], "language": info.language,
        "model": args.model, "words": words, "segments": segs})

    # Version lisible : chaque mot précédé de son numéro, pour désigner les coupes.
    with open(paths["transcript_txt"], "w", encoding="utf-8") as f:
        f.write(f"# Transcription de {voice.name} — [n] = numéro du mot\n\n")
        for s in segs:
            a, b = s["words"]
            line = " ".join(f"[{w['i']}]{w['w']}" for w in words[a:b + 1])
            f.write(f"{tc(s['start'])}  {line}\n")
    print(f"[OK] {paths['transcript']}\n[OK] {paths['transcript_txt']}")


if __name__ == "__main__":
    main()
