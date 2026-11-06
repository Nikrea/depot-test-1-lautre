"""Recompose le livret : texte retapé (recettes/*.json), photos des plats retouchées, mise en page neuve.
Usage : python3 outils/recomposer.py   ->  recompose/livre-recompose.html, puis outils/imprimer.js en fait le PDF."""
import json, re, html
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
SORTIE = RACINE/'recompose'
SEMAINE = 'Semaine 45 | 2026'
FOURNISSEURS = '*En cas de problème d’approvisionnement, nous favorisons des fournisseurs européens de qualité équivalente.'
ALLERGENES = ('Attention, certains ingrédients peuvent contenir des allergènes. En cas d’allergie, référez-vous aux '
              'étiquettes des ingrédients avant de cuisiner. Les allergènes et traces d’allergènes sont indiqués en gras, '
              'en italique ou en MAJUSCULE sur les étiquettes.')

def t(s):
    """Texte sûr, **gras** et fraction ⅓ (absente des polices) en vraie fraction typographique."""
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s.replace('⅓', '<span class="frac">1/3</span>')

def pastilles(r):
    out = [f'<span class="num">Recette {r["numero"]}</span>', f'<span class="pastille temps">À table en {t(r["temps"])}</span>']
    for tag in r.get('tags', []):
        out.append(f'<span class="pastille{" epice" if tag.startswith("Épicé") else ""}">{t(tag)}</span>')
    if r.get('badge'):
        out.append(f'<span class="pastille">{t(r["badge"])}</span>')
    return '<div class="etiquettes">' + ''.join(out) + '</div>'

def pied(p):
    return f'<div class="pied"><span><b>Hello L’Antihéros</b> · {SEMAINE}</span><span>{p}</span></div>'

def ouverture(r, p):
    ing = ''.join(f'<li><span class="n">{t(n)}{"<sup>*</sup>" if frais else ""}</span><span class="q">{t(q)}</span></li>'
                  for n, q, frais in r['ingredients'])
    ajout = ''.join(f'<li><span class="n">{t(n)}</span><span class="q">{t(q)}</span></li>' for n, q in r['a_ajouter'])
    note = r.get('note', '')
    if note.endswith('*'):
        note += ' ' + FOURNISSEURS
    return f'''
<section class="page ouverture{' longue' if len(r['ingredients']) > 10 else ''}">
  <div class="photo"><img src="photos/{r["numero"]}.jpg" alt=""></div>
  <div class="corps">
    {pastilles(r)}
    <h1>{t(r["titre"])}</h1>
    <p class="sous">{t(r["sous_titre"])}</p>
    <div class="colonnes">
      <div class="bloc">
        <h4>Dans la box <small>pour 6 personnes</small></h4>
        <ul class="liste">{ing}</ul>
        <p class="frais">* à conserver au réfrigérateur</p>
      </div>
      <div>
        <div class="bloc"><h4>À ajouter vous-même</h4><ul class="liste">{ajout}</ul></div>
        <div class="bloc"><h4>Ustensiles</h4><p class="ustensiles">{t(r["ustensiles"])}</p></div>
      </div>
    </div>
  </div>
  {f'<p class="note-bas">{t(note)}</p>' if note else ''}
  {pied(p)}
</section>'''

def etapes(r, p):
    blocs = []
    for i, e in enumerate(r['etapes'], 1):
        pts = ''.join(f'<li>{t(x)}</li>' for x in e['points'])
        ast = ''
        if e.get('astuce'):
            ast = f'<div class="astuce"><b>{t(e["astuce"][0])}</b>{t(e["astuce"][1])}</div>'
        blocs.append(f'<article class="etape"><div class="chiffre">{i}</div><div><h3>{t(e["titre"])}</h3>'
                     f'<ul>{pts}</ul>{ast}</div></article>')
    nut = ''
    for nom, port, cent in r['nutrition']:
        sous = ' class="sous"' if nom.startswith('dont') else ''
        nut += f'<tr{sous}><td>{t(nom)}</td><td>{t(port)}</td><td>{t(cent)}</td></tr>'
    return f'''
<section class="page etapes-page">
  <div class="tete">
    <div><div class="kicker">Recette {r["numero"]} · pas à pas</div><h2>{t(r["titre"])}</h2></div>
  </div>
  <div class="etapes">{''.join(blocs)}</div>
  <div class="reperes">
    <div><h4>Valeurs nutritionnelles</h4>
      <table class="nutri"><thead><tr><th></th><th>Par portion</th><th>Pour 100 g</th></tr></thead><tbody>{nut}</tbody></table></div>
    <div class="allergenes"><h4>Allergènes</h4><p>{ALLERGENES}</p><div class="fin">À vos fourchettes !</div></div>
  </div>
  {pied(p)}
</section>'''

def main():
    recettes = sorted((json.loads(f.read_text(encoding='utf-8')) for f in (RACINE/'recettes').glob('*.json')),
                      key=lambda r: r['numero'])
    mosaique = ''.join(f'<figure><img src="photos/{r["numero"]}.jpg" alt=""></figure>' for r in recettes)
    couverture = f'''
<section class="page couverture">
  <div class="haut">
    <span class="eyebrow">Ma box du 5 novembre</span>
    <h1>Hello<span>L’Antihéros</span></h1>
    <p class="accroche">Au menu cette semaine : {len(recettes)} recettes à cuisiner pas à pas.</p>
    <div class="infos"><div>Recettes<b>{len(recettes)}</b></div><div>Pour<b>6 personnes</b></div><div>Édition<b>{SEMAINE}</b></div></div>
  </div>
  <div class="mosaique">{mosaique}</div>
</section>'''
    entrees, pages, p = '', '', 3
    for r in recettes:
        entrees += f'''
  <div class="entree">
    <div class="vignette"><img src="photos/{r["numero"]}.jpg" alt=""></div>
    <div><div class="meta">Recette {r["numero"]} · {t(r["temps"])}</div><h3>{t(r["titre"])}</h3><p>{t(r["sous_titre"])}</p></div>
    <div class="p">{p}</div>
  </div>'''
        pages += ouverture(r, p) + etapes(r, p + 1)
        p += 2
    sommaire = f'''
<section class="page sommaire">
  <div class="kicker">Sommaire</div>
  <h2>Au menu</h2>
  <p class="intro">C’est parti ! Planifiez l’ordre des recettes selon la date de péremption inscrite sur l’étiquette de vos ingrédients. Rincez les fruits et légumes.</p>
  {entrees}
  <p class="note">Recettes de la box HelloFresh, retranscrites et remises en page. Quantités pour 6 personnes.</p>
  {pied(2)}
</section>'''
    doc = f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Hello L’Antihéros</title>
<link rel="stylesheet" href="../outils/gabarit_livre.css"></head>
<body>{couverture}{sommaire}{pages}</body></html>'''
    SORTIE.mkdir(exist_ok=True)
    (SORTIE/'livre-recompose.html').write_text(doc, encoding='utf-8')
    print('livre-recompose.html :', 2 + 2 * len(recettes), 'pages')

if __name__ == '__main__':
    main()
