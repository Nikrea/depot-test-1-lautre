# Atelier Étoile — miniatures YouTube

Un outil dans le navigateur pour fabriquer des miniatures dans le style « RÊVE / NOUS / OUBLIÉ » :
une image retravaillée, **un seul mot géant**, toujours le même lettrage, une **étoile à quatre branches**
à la place du creux d'une lettre, et le sujet de l'image qui passe **devant** le mot.

Page publiée : https://claude.ai/artifact/TkmFJYUKrmxT6Wh4JWoufa

## Utilisation

1. **Choisir une image** (ou la glisser / la coller). Le sujet est détouré automatiquement par une IA qui
   tourne dans le navigateur : l'image ne quitte pas l'appareil. Le modèle (56 Mo) se télécharge au premier
   détourage, puis l'analyse prend 10 à 30 s.
2. **Taper le mot.** L'étoile se place seule dans la première lettre qui a un creux (O, R, A, D, P, B, Q…) ;
   les pastilles permettent de choisir une autre lettre ou de l'enlever.
3. **Placer** : onglet *Texte* pour glisser le mot, *Image* pour recadrer et zoomer, *Pinceau* pour
   corriger ce qui passe devant (« Mettre devant » / « Mettre derrière »).
4. **Ambiance** : Éclat (par défaut), Ciné, Rêve, Nuit, Or, Naturel, avec les réglages fins
   (lumière, contraste, couleurs, chaleur, relief, netteté, lueur, vignette, teinte ciné).
5. **Exporter la miniature** : JPG 1280 × 720 sous 2 Mo (limite YouTube), ou PNG.

L'aperçu « Dans le fil YouTube » montre la miniature à la taille réelle du fil, avec la durée en bas à droite.

## Le lettrage

Police **Anton** (Google Fonts), retravaillée à chaque rendu pour coller aux miniatures de référence :
angles arrondis et graisse renforcée (flou gaussien + seuil sur le mot entier), légère courbure
(bords un peu plus hauts que le centre), dégradé blanc qui prend un reflet de la couleur de la scène,
ombre portée douce et ombre du sujet sur les lettres. L'étoile est découpée après avoir bouché le creux
de la lettre ; elle est réduite automatiquement tant qu'elle déborderait du contour.

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | toute l'application (publiée telle quelle comme artefact) |
| `sample/lune.jpg`, `sample/lune-masque.png` | l'exemple d'ouverture (photo NASA Apollo 11, domaine public) et son détourage |
| `tools/build_model.py` | prépare le modèle de détourage dans `model/` (non versionné, 56 Mo) |

## Modèle de détourage

IS-Net « general use » (DIS, licence Apache-2.0) via ONNX Runtime Web 1.17.3, exécuté dans un worker
(WASM, un fil). Si le navigateur interdit le WebAssembly, l'outil essaie la carte graphique (WebGL),
puis bascule sur le pinceau. Pour régénérer `model/` avant une nouvelle publication :

```bash
pip install onnx onnxruntime numpy
python3 miniatures/tools/build_model.py
```

Le script retire les sorties inutiles, fige les formes, convertit les `Resize` pour WebGL et stocke les
poids en int8 par canal (écart moyen sur le masque : 0,04 %). Le navigateur recolle le tout en float32.
