"""Lance tout le pipeline d'un coup.

    python run_all.py D:/Projets/MaVideo              étapes 1 à 4, puis s'arrête pour vérifier
    python run_all.py D:/Projets/MaVideo --resolve    ... et construit la timeline dans Resolve
    python run_all.py D:/Projets/MaVideo --fcpxml     ... ou exporte un FCPXML à importer
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent / "pipeline"


def step(script, *args):
    print(f"\n=== {script} " + "=" * (50 - len(script)))
    if subprocess.run([sys.executable, str(HERE / script), *args]).returncode != 0:
        sys.exit(f"[ERREUR] {script} a échoué, arrêt.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projet")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--fps", default="24")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--fcpxml", action="store_true")
    args = ap.parse_args()

    step("transcribe.py", args.projet, "--model", args.model)
    step("derush.py", args.projet, "--fps", args.fps)
    step("index_broll.py", args.projet)
    step("match_broll.py", args.projet)
    if args.resolve:
        step("to_resolve.py", args.projet)
    if args.fcpxml:
        step("to_fcpxml.py", args.projet)
    if not (args.resolve or args.fcpxml):
        print("\nVérifie _derush/derush_rapport.md et _derush/placements_rapport.md, "
              "puis : python pipeline/to_resolve.py " + args.projet)


if __name__ == "__main__":
    main()
