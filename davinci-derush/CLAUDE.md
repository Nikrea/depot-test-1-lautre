# Dérush automatique + calage des B-rolls dans DaVinci Resolve

Tu aides un YouTuber (Windows, **DaVinci Resolve Studio**, tournage à **24 i/s**) à monter
une vidéo : dérusher sa voix puis poser les B-rolls sur ce qu'il dit.
Réponds en français. Les scripts sont dans `pipeline/` ; lis le docstring d'un script avant
d'en changer les options.

## Structure d'un projet vidéo (dossier donné par l'utilisateur)

```
MaVideo/
  voix/        UN fichier : la narration (wav, mp3, ou vidéo face cam)
  broll/       les plans d'illustration (vidéos et photos, sous-dossiers permis)
  script.txt   facultatif : le texte prévu
  _derush/     créé par le pipeline (tout ce que tu produis va ici)
```

## Déroulé — suis ces étapes dans l'ordre

1. **Transcrire** : `python pipeline/transcribe.py <projet>` (large-v3 par défaut ;
   `--model medium` si pas de GPU et que c'est trop lent).
2. **Dérush auto** : `python pipeline/derush.py <projet>`.
3. **Ta relecture du dérush** — c'est là que tu apportes le plus :
   - lis `_derush/transcript_mots.txt` (chaque mot a son numéro `[n]`) et
     `_derush/derush_rapport.md` (ce que l'automatique a coupé) ;
   - si `script.txt` existe, compare : ce qui n'est pas dans le script et ressemble
     à une prise ratée, un aparté (« attends », « je recommence », « coupe ça ») ou une
     phrase redite est à couper ; **garde toujours la dernière prise complète** ;
   - une coupe auto est fausse (répétition voulue, anaphore, effet de style) → restaure-la ;
   - écris `_derush/decisions.json` puis relance `derush.py` :
     `{"remove": [[début, fin, "raison"]], "keep": [[début, fin]]}` (numéros de mots, bornes incluses) ;
   - ne coupe jamais au milieu d'une idée : en cas de doute, garde et signale-le.
4. **Inventaire des B-rolls** : `python pipeline/index_broll.py <projet>`.
5. **Ta description des B-rolls** : ouvre chaque planche `_derush/thumbs/Bxxx.jpg`
   (3 images : début, milieu, fin du clip) et remplis dans `_derush/broll_index.json`
   `"description"` (une phrase concrète : sujet, lieu, moment, valeur de plan, mouvement)
   et `"tags"` (5 à 12 mots-clés en français, synonymes inclus). Ne touche pas aux autres champs.
6. **Placement** : `python pipeline/match_broll.py <projet> --force` donne un premier jet par
   mots-clés. Puis **améliore `_derush/placements.json` par le sens**, avec
   `_derush/montage_texte.txt` (les phrases avec leur timecode de timeline) :
   - le B-roll arrive sur le mot qui l'appelle (environ 0,25 s avant), dure 2 à 6 s ;
   - il illustre aussi les idées abstraites (« la peur » → plan sombre, foule, visage) ;
   - pas de chevauchement sur V2, un même clip au plus deux fois et jamais deux fois de suite ;
   - laisse de l'air : pas de B-roll pendant les phrases d'accroche face cam ou les moments
     forts où on doit voir le visage (si la voix est une vidéo face cam) ;
   - `rec_in`/`rec_out` en images de timeline (24 i/s, 0 = début), `src_in_s` en secondes
     dans le clip (vérifie que `src_in_s + durée <= duration` du clip).
7. **Montrer avant de monter** : résume le dérush (durée avant/après, coupes notables) et
   le placement (tableau timecode → clip → pourquoi) et **attends le feu vert**.
8. **Construire dans Resolve** (Resolve Studio ouvert) : `python pipeline/to_resolve.py <projet>`.
   Ça crée un NOUVEAU projet : rien d'existant n'est modifié.
   Si le scripting ne répond pas : `python pipeline/test_resolve.py` pour diagnostiquer, ou
   repli `python pipeline/to_fcpxml.py <projet>` puis Fichier > Importer > Timeline dans Resolve.

## Règles

- Ne supprime ni ne déplace jamais les fichiers de `voix/` et `broll/`.
- Ne modifie pas un projet Resolve existant : `to_resolve.py` en crée toujours un nouveau.
- Si une étape échoue, lis l'erreur, corrige la cause (chemin, FFmpeg absent, Resolve fermé)
  et relance seulement cette étape ; chaque étape réutilise les fichiers de `_derush/`.
- Les retouches à la main de l'utilisateur dans `placements.json` ou `decisions.json` sont
  prioritaires : ne les écrase pas sans le dire (`match_broll.py` refuse d'écraser sans `--force`).
