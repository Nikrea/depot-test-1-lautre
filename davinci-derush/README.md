# Dérush automatique + calage des B-rolls dans DaVinci Resolve

Tu poses ta voix et tes plans dans un dossier. Claude :

1. **transcrit** ta voix mot à mot (Whisper, en local, sur ton PC) ;
2. **dérushe** : coupe les blancs, les « euh », les bégaiements et les prises ratées
   (il garde la dernière prise) ;
3. **regarde tes B-rolls** (3 images par clip) et les décrit ;
4. **pose chaque B-roll** sur le passage où tu en parles ;
5. **construit la timeline dans Resolve Studio** : la voix sur V1/A1, les B-rolls sur V2,
   un marqueur bleu qui explique chaque choix.

Pensé pour **Windows + DaVinci Resolve Studio + 24 i/s**.

---

## 1. Installation (une seule fois, environ 15 min)

### a) Claude Code sur ton PC
C'est indispensable : Claude doit tourner **sur la machine où est installé Resolve**.
- Soit l'**app Claude Desktop** (onglet Code) ;
- soit dans PowerShell : `npm install -g @anthropic-ai/claude-code` (il faut [Node.js](https://nodejs.org)), puis `claude`.

### b) Récupérer ce dossier
```powershell
git clone https://github.com/nikrea/depot-test-1-lautre.git
cd depot-test-1-lautre\davinci-derush
```
(Pas de git ? Bouton **Code > Download ZIP** sur GitHub, puis dézippe.)

### c) Lancer l'installateur
```powershell
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```
Il installe Python, FFmpeg et Whisper, pose les variables d'environnement de Resolve et
ajoute les bibliothèques GPU si tu as une carte NVIDIA.

### d) Activer le scripting dans Resolve
**DaVinci Resolve > Préférences > Système > Général > External scripting using → `Local`**,
puis **redémarre Resolve**.

### e) Vérifier
Ferme et **rouvre** PowerShell (pour que les variables soient prises en compte), Resolve ouvert :
```powershell
python pipeline\test_resolve.py
```
→ `[OK] DaVinci Resolve Studio 20.x — projet ouvert : ...`

---

## 2. Préparer un projet vidéo

```
D:\YouTube\Titanic\
  voix\        narration.wav        ← UN seul fichier (wav, mp3 ou vidéo face cam)
  broll\       titanic_proue_nuit.mp4, iceberg_drone.mov, new_york_1912.jpg ...
  script.txt   (facultatif) ton texte, ça aide beaucoup à repérer les prises ratées
```

**Les 4 règles d'or**
- **Des noms de fichiers parlants** : `foule_manifestation_paris.mp4` plutôt que `C0042.MP4`.
  Claude regarde aussi les images, mais un bon nom aide toujours.
- **Quand tu te plantes en enregistrant** : une petite pause, puis **redis toute la phrase**.
  La dernière prise est gardée automatiquement.
- **Tout en 24 i/s** autant que possible. Les clips à 25 ou 30 i/s marchent quand même
  (Resolve les adapte).
- **Formats RAW** (.braw, .r3d) : fais des proxys .mov, que FFmpeg sait lire.

---

## 3. Lancer le montage avec Claude (méthode recommandée)

Dans PowerShell, depuis le dossier `davinci-derush` :
```powershell
claude
```
puis écris par exemple :

> Monte le projet `D:\YouTube\Titanic`. Dérushe ma voix, décris mes B-rolls, place-les
> par le sens et montre-moi le résultat avant de construire la timeline dans Resolve.

Claude suit le fichier `CLAUDE.md` : il lance les étapes, relit lui-même les coupes, regarde
chaque B-roll et te montre un tableau à valider. Après ton « go », il construit tout dans Resolve.

**Quelques demandes utiles ensuite**
- « Garde un peu plus de respiration entre les phrases » → `--pad-phrase 0.5`
- « Coupe plus serré, style rythme rapide » → `--max-pause 0.2 --pad-after 0.08`
- « Remets la phrase sur les pyramides, je la voulais » → restauration via `decisions.json`
- « Pas de B-roll pendant les 10 premières secondes, je suis face cam »
- « Utilise plus souvent le plan du drone »

---

## 4. Sans Claude (tout automatique, par mots-clés)

```powershell
python run_all.py D:\YouTube\Titanic            # étapes 1 à 4, puis vérifie les rapports
python pipeline\to_resolve.py D:\YouTube\Titanic # construit la timeline dans Resolve
```
À vérifier dans `D:\YouTube\Titanic\_derush\` :
`derush_rapport.md` (ce qui a été coupé) et `placements_rapport.md` (quel B-roll, où, pourquoi).

---

## 5. Ce qui se passe dans Resolve

`to_resolve.py` crée un **nouveau projet** « Titanic - derush 2026-10-10 14h32 » réglé à 24 i/s,
1920×1080 (`--resolution 3840x2160` pour la 4K) :

| Piste | Contenu |
|---|---|
| V1 / A1 | ta voix dérushée (et ta vidéo si c'est une face cam) |
| V2 | les B-rolls, **sans leur son** |
| Marqueurs bleus | le B-roll et le mot-clé qui l'a déclenché |

Tes autres projets ne sont jamais modifiés.

**Plan B : le FCPXML.** Si le scripting refuse de marcher :
`python pipeline\to_fcpxml.py D:\YouTube\Titanic`, puis dans Resolve
**Fichier > Importer > Timeline…** et choisis `_derush\timeline.fcpxml`
(règle d'abord le projet à 24 i/s).

---

## 6. Dépannage

| Problème | Solution |
|---|---|
| `Resolve ne répond pas` | Resolve Studio ouvert ? Scripting sur **Local** ? Resolve redémarré ensuite ? |
| `Module DaVinciResolveScript introuvable` | relance `setup_windows.ps1`, puis **rouvre** le terminal |
| `ffmpeg introuvable` | `winget install Gyan.FFmpeg`, puis rouvre le terminal |
| Transcription très lente | pas de GPU NVIDIA : `--model medium` ou `small` (un peu moins précis) |
| Plantage GPU (`cudnn`…) | `python pipeline\transcribe.py <projet> --device cpu` |
| Un « euh » est resté | Whisper ne l'a pas écrit : demande à Claude de couper ce passage |
| Coupe trop sèche | augmente `--pad-after` (0,15 → 0,25) |
| Photo plus courte que prévu | Préférences > Utilisateur > Montage > **Durée standard des images fixes** : mets 10 s |

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `pipeline/transcribe.py` | Whisper : timecode de chaque mot (consigne qui force l'écriture des « euh ») |
| `pipeline/derush.py` | blancs, hésitations, bégaiements, reprises ; coupes calées sur les vrais silences (FFmpeg) |
| `pipeline/index_broll.py` | durée, cadence, mots-clés du nom de fichier, planche de 3 images par clip |
| `pipeline/match_broll.py` | premier jet du placement par mots-clés (que Claude affine par le sens) |
| `pipeline/to_resolve.py` | construit le projet et la timeline par l'API Resolve |
| `pipeline/to_fcpxml.py` | plan B : export FCPXML 1.9 |
| `pipeline/test_resolve.py` | teste la connexion à Resolve |
| `CLAUDE.md` | la méthode de montage que Claude suit |
