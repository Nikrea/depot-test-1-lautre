# Livre numérique : Hello L'Antihéros

`livre.html` est le livre complet en **un seul fichier** (images, police et moteur intégrés).
Il s'ouvre dans n'importe quel navigateur, même hors connexion.

- **Tourner les pages** : glisser la page au doigt ou à la souris, ou les flèches ‹ ›, ou le clavier ← →.
- **Lire** : ouvre la page en grand, remise à l'endroit (les fiches recettes sont imprimées de côté).
  Pincer ou toucher deux fois pour zoomer, glisser pour changer de page.
- **Sommaire** : les 4 recettes, avec vignettes.
- Sur ordinateur et tablette à l'horizontale : double page. Sur téléphone : une page à la fois.

Deux autres formats, pour les téléphones dont l'app n'affiche pas les pages HTML :

- **`livre.epub`** : à ouvrir dans **Livres** (iPhone, iPad, Mac) ou Play Livres (Android). On y tourne les pages
  au doigt avec l'effet de page qui se courbe ; les fiches recettes sont remises à l'endroit (tourner le téléphone
  pour les lire en grand).
- **`livre.pdf`** : s'ouvre partout, fiches à l'endroit, sommaire dans les signets.

## Comment il est fabriqué

| Étape | Script | Ce qu'il fait |
|---|---|---|
| 1 | `outils/redresser.py` | recadre chaque photo et corrige la perspective (coins dans `PAGES`), puis aligne les fiches d'un même modèle entre elles |
| 2 | `outils/couverture.py` | remplace « NICOLAS » par « L'ANTIHÉROS » sur la couverture, dans le style du titre |
| 3 | `outils/nettoyer.py` | blanchit le papier, uniformise la lumière, ravive les couleurs, affine |
| 4 | `outils/construire.py` | assemble `livre.html` à partir de `livre.json` (ordre des pages, sens de lecture, sommaire) |
| 5 | `outils/exporter.py` | fabrique `livre.pdf` et `livre.epub` (pages remises à l'endroit) |

```bash
pip install opencv-python-headless pillow img2pdf pypdf
python3 outils/redresser.py && python3 outils/couverture.py
cd outils && python3 nettoyer.py && cd .. && python3 outils/construire.py && python3 outils/exporter.py
```

**Ajouter des pages** : mettre les photos dans `photos/` (10.jpg, 11.jpg…), ajouter leurs coins dans
`PAGES` (`outils/redresser.py`), une ligne par page dans `livre.json`, puis relancer les scripts.

Crédits : moteur de pages [StPageFlip](https://github.com/Nodlik/StPageFlip) (MIT),
police Archivo Black (SIL Open Font License).
