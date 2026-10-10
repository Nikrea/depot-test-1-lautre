"""Vérifie que Python arrive à parler à DaVinci Resolve (à lancer Resolve ouvert)."""
import os
import sys

api = os.environ.get("RESOLVE_SCRIPT_API")
lib = os.environ.get("RESOLVE_SCRIPT_LIB")
print(f"RESOLVE_SCRIPT_API = {api}\nRESOLVE_SCRIPT_LIB = {lib}")
if not api or not lib:
    sys.exit("[ERREUR] Variables absentes : lance setup_windows.ps1 puis ROUVRE le terminal.")
if not os.path.exists(lib):
    sys.exit(f"[ERREUR] {lib} n'existe pas : Resolve est installé ailleurs ? Corrige RESOLVE_SCRIPT_LIB.")
sys.path.append(os.path.join(api, "Modules"))
try:
    import DaVinciResolveScript as dvr
except ImportError as e:
    sys.exit(f"[ERREUR] Import du module Resolve impossible : {e}")
resolve = dvr.scriptapp("Resolve")
if resolve is None:
    sys.exit("[ERREUR] Pas de réponse. Resolve Studio est ouvert ? Préférences > Système > Général > "
             "External scripting using = Local ? (redémarre Resolve après l'avoir changé)")
project = resolve.GetProjectManager().GetCurrentProject()
print(f"[OK] {resolve.GetProductName()} {resolve.GetVersionString()} — projet ouvert : "
      f"{project.GetName() if project else 'aucun'}")
