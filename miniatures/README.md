# Atelier Étoile — miniatures YouTube

Un outil dans le navigateur pour fabriquer des miniatures dans le style « RÊVE / NOUS / OUBLIÉ » :
une image retravaillée, **un seul mot géant**, toujours le même lettrage, une **étoile à quatre branches**
à la place du creux d'une lettre, et le sujet de l'image qui passe **devant** le mot.

Page publiée : https://claude.ai/artifact/TkmFJYUKrmxT6Wh4JWoufa

## Utilisation

1. **Choisir une image** (ou la glisser / la coller). Le sujet est détouré automatiquement par une IA qui
   tourne dans le navigateur : l'image ne quitte pas l'appareil. Le modèle (56 Mo) se télécharge au premier
   détourage, puis l'analyse prend 20 à 60 s (deux passes).
2. **Taper le mot.** Il se place seul, toujours au même endroit (centré, à mi-hauteur). L'étoile se loge dans la
   première lettre qui a un creux ; les pastilles permettent de choisir une autre lettre ou de l'enlever.
3. **Cadrer l'image** sous le mot (onglet *Image*), corriger le détourage au *Pinceau* si besoin.
4. **Retouche de l'image** : un style de lumière (*Lumineux* ou *Dramatique*, proposé d'après l'image) et
   cinq niveaux : *Brut, Doux, Équilibré, Vif, Intense*. Les réglages fins restent accessibles.
5. **Exporter** : *Exporter en 4K* (3840 × 2160, la résolution que YouTube recommande ; envoi depuis un
   ordinateur, limite 50 Mo) ou *Version téléphone* (1920 × 1080, moins de 2 Mo : la limite de YouTube depuis
   un téléphone). L'aperçu se travaille en 1280 × 720 ; à l'export, toute la miniature est recalculée à la
   taille demandée.

Le travail en cours est gardé sur l'appareil (image et détourage dans IndexedDB, cadrage et réglages dans
localStorage) : si la page se recharge, il revient tel quel. *Repartir de l'exemple* l'efface.

L'aperçu « Dans le fil YouTube » montre la miniature à la taille réelle du fil, avec la durée en bas à droite.

## La retouche

Ce n'est pas un filtre posé sur l'image : chaque image est mesurée (point noir, point blanc, médiane,
saturation moyenne, couleur des lumières par rapport aux ombres) et le dosage de chaque niveau en découle.
Le calcul se fait en OKLab (clarté, chroma, teinte perceptuelles) :

- **tonalité** : une partie seulement de l'écart aux points noir et blanc mesurés est reprise, puis les ombres
  et les hautes lumières sont comprimées en douceur (genou) : jamais de noir bouché ni de blanc brûlé, même
  curseurs à fond. « Lumière » agit sur les tons moyens ;
- **couleurs** : vibrance qui ménage les gris et le déjà saturé, réglages par famille de teintes (bleus plus
  profonds, jaunes plus lumineux, orange retenu pour la peau) ;
- **contraste des couleurs** : chaque pixel s'écarte de la teinte moyenne de son voisinage et de l'image, et
  les lumières sont poussées vers la couleur de la lumière de la scène, les ombres vers son opposé. La palette
  s'ouvre sans dominante imposée ; les gris et les noirs restent neutres ;
- **sujet** : grâce au détourage, le sujet est éclairci et détaillé, le fond retenu ;
- **saturation retenue** : le dosage tient compte des couleurs les plus vives de l'image (une image déjà vive
  n'est presque pas poussée) et, à l'approche de la limite de l'écran, la couleur est ramenée progressivement
  vers le gris de même clarté : les aplats restent modelés ;
- le relief et la netteté ignorent les très petits écarts (bruit, blocs de compression) et sont plafonnés
  (pas de halo).

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
- **position fixe** : centré, à mi-hauteur (réglable), avec ombre portée (couleur au choix, noire par défaut)
  et halo en option.

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
(WASM, un fil). Deux passes : l'image entière, puis un zoom sur le sujet. La première donne le cœur du sujet,
la seconde ses bords ; le contour est ensuite calé sur les vrais bords de l'image (filtre guidé), les zones
hésitantes sont tranchées et les îlots retirés, pour éviter tout voile à moitié transparent autour du sujet. Si le navigateur interdit le WebAssembly, l'outil essaie la carte graphique (WebGL),
puis bascule sur le pinceau. Pour régénérer `model/` avant une nouvelle publication :

```bash
pip install onnx onnxruntime numpy
python3 miniatures/tools/build_model.py
```

Le script retire les sorties inutiles, fige les formes, convertit les `Resize` pour WebGL et stocke les
poids en int8 par canal (écart moyen sur le masque : 0,04 %). Le navigateur recolle le tout en float32.
