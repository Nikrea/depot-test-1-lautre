# Atelier Étoile — miniatures YouTube

Un outil dans le navigateur pour fabriquer des miniatures dans le style « RÊVE / NOUS / OUBLIÉ » :
une image retravaillée, **un seul mot géant**, toujours le même lettrage, une **étoile à quatre branches**
à la place du creux d'une lettre, et le sujet de l'image qui passe **devant** le mot.

Page publiée : https://claude.ai/artifact/TkmFJYUKrmxT6Wh4JWoufa

## Utilisation

1. **Choisir une image** (ou la glisser / la coller). Le sujet est détouré automatiquement par une IA qui
   tourne dans le navigateur : l'image ne quitte pas l'appareil. Le modèle (56 Mo) se télécharge au premier
   détourage, puis l'analyse prend 10 à 30 s.
2. **Taper le mot.** Il se place seul, toujours au même endroit (centré, à mi-hauteur). L'étoile se loge dans la
   première lettre qui a un creux ; les pastilles permettent de choisir une autre lettre ou de l'enlever.
3. **Cadrer l'image** sous le mot (onglet *Image*), corriger le détourage au *Pinceau* si besoin.
4. **Retouche de l'image** : un style de lumière (*Lumineux* ou *Dramatique*, proposé d'après l'image) et
   cinq niveaux, de *Brut* à *Extrême*. Les réglages fins restent accessibles.
5. **Exporter la miniature** : JPG 1280 × 720 sous 2 Mo (limite YouTube), ou PNG.

L'aperçu « Dans le fil YouTube » montre la miniature à la taille réelle du fil, avec la durée en bas à droite.

## La retouche

Ce n'est pas un filtre posé sur l'image : chaque image est mesurée (point noir, point blanc, médiane,
saturation moyenne, couleur des lumières par rapport aux ombres) et le dosage de chaque niveau en découle.
Le calcul se fait en OKLab (clarté, chroma, teinte perceptuelles) :

- **tonalité** : étirement entre les points noir et blanc mesurés, ombres débouchées (Lumineux) ou noirs
  profonds et contraste (Dramatique) ;
- **couleurs** : vibrance qui ménage les gris et le déjà saturé, réglages par famille de teintes (bleus plus
  profonds, jaunes plus lumineux, orange retenu pour la peau) ;
- **contraste des couleurs** : chaque pixel s'écarte de la teinte moyenne de son voisinage et de l'image, et
  les lumières sont poussées vers la couleur de la lumière de la scène, les ombres vers son opposé. La palette
  s'ouvre sans dominante imposée ; les gris et les noirs restent neutres ;
- **sujet** : grâce au détourage, le sujet est éclairci et détaillé, le fond retenu ;
- ce qui sort du gamut est ramené vers le gris de même clarté, jamais écrêté.

Limite à connaître : l'outil retravaille les pixels existants. Il ne redessine pas l'image (ajouter du
feuillage, des rayons, des détails) comme le fait une IA générative.

Si la vue le permet, le bouton **Faire régler par Claude** envoie l'image à Claude, qui choisit le dosage
de chaque teinte et l'explique en une phrase.

## Le lettrage

La police est celle de la chaîne, **reconstruite d'après les planches de référence** (`font/refs/`) :
blocs très lourds, fentes fines à bouts ronds, encoches, petits angles arrondis.

- **Lettres décalquées** sur les planches, après redressement de l'arche : A B D E F H I L M N O P R S T U V,
  les accents aigu, grave et circonflexe, l'apostrophe ;
- **lettres construites** avec le même vocabulaire : C G J K Q W X Y Z, les chiffres, la ponctuation, le tréma,
  la cédille, Œ et Æ (le G reprend celui de la miniature « MENSONGE ») ;
- l'apostrophe est celle de la planche réduite à 60 %, avec du blanc de chaque côté ; après un L elle se pose
  au-dessus du pied, et le A qui suit se rapproche.

Le rendu suit les planches :

- **taille** : le mot vise 59 % de la hauteur de l'image ou 88 % de sa largeur (jusqu'à 94,5 % pour un mot long) ;
- **arche** : haut droit, bas en arc (les lettres des bords descendent plus bas). L'arche du haut se règle
  aussi : négative, elle donne le nœud papillon de « NOTRE FUTUR » ; positive, l'arc de « PÈRE » ;
- **étoile** : une étincelle à quatre branches posée sur la fente de la lettre. Elle va dans le O ; sans O,
  dans le premier A ou R ; sinon dans la première lettre à creux ;
- **position fixe** : centré, à mi-hauteur (réglable), avec ombre portée et halo en option.

Pour régénérer la police (et la réembarquer dans `index.html`) :

```bash
pip install numpy opencv-python-headless scipy fonttools potracer brotli
python3 miniatures/tools/build_font.py
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | toute l'application (publiée telle quelle comme artefact) |
| `sample/lune.jpg`, `sample/lune-masque.png` | l'exemple d'ouverture (photo NASA Apollo 11, domaine public) et son détourage |
| `font/AtelierEtoile.otf`, `.woff2` | la police reconstruite (71 caractères) ; `font/specimen.png` la montre en entier |
| `font/refs/` | les planches de référence d'où viennent les lettres |
| `tools/build_font.py`, `tools/font_glyphs.py` | fabrication de la police |
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
