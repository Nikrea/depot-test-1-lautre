# Installation du pipeline de dérush (Windows + DaVinci Resolve Studio)
# Clic droit > "Exécuter avec PowerShell", ou dans un terminal :
#   powershell -ExecutionPolicy Bypass -File setup_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "`n=== 1. Python" -ForegroundColor Cyan
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python absent : installation via winget..."
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    Write-Host "Ferme et rouvre PowerShell, puis relance ce script." -ForegroundColor Yellow
    exit 1
}
python --version

Write-Host "`n=== 2. FFmpeg" -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    Write-Host "FFmpeg installé : il sera dans le PATH après réouverture du terminal." -ForegroundColor Yellow
} else { Write-Host "OK" }

Write-Host "`n=== 3. Bibliothèques Python" -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "`n=== 4. Variables d'environnement pour le scripting Resolve" -ForegroundColor Cyan
$api = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$lib = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
if (-not (Test-Path $lib)) { Write-Host "ATTENTION : $lib introuvable (Resolve installé ailleurs ?)" -ForegroundColor Yellow }
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_API", $api, "User")
[Environment]::SetEnvironmentVariable("RESOLVE_SCRIPT_LIB", $lib, "User")
$pp = [Environment]::GetEnvironmentVariable("PYTHONPATH", "User")
$mod = "$api\Modules\"
if (-not $pp -or -not $pp.Contains($mod)) {
    $new = if ($pp) { "$pp;$mod" } else { $mod }
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $new, "User")
}
Write-Host "OK"

Write-Host "`n=== 5. GPU NVIDIA (facultatif, transcription ~10x plus rapide)" -ForegroundColor Cyan
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
    Write-Host "Bibliothèques CUDA installées."
} else { Write-Host "Pas de GPU NVIDIA détecté : la transcription tournera sur le processeur." }

Write-Host "`nTERMINÉ." -ForegroundColor Green
Write-Host "Dans Resolve : Préférences > Système > Général > External scripting using = Local, puis redémarre Resolve."
Write-Host "Ensuite, ROUVRE ce terminal et teste :  python pipeline\test_resolve.py"
