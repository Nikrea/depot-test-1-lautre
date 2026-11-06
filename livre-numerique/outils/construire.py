"""Assemble le livre en un seul fichier HTML autonome (images, police et moteur intégrés).
Usage : python3 outils/construire.py   ->  livre.html"""
import base64, io, json
from pathlib import Path
from PIL import Image

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent

def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()

def webp(p):
    """Page en WebP : deux fois plus léger que le JPEG, texte toujours net au zoom."""
    b = io.BytesIO(); Image.open(p).save(b, 'WEBP', quality=74, method=6)
    return base64.b64encode(b.getvalue()).decode()

def main():
    livre = json.loads((RACINE/'livre.json').read_text(encoding='utf-8'))
    w, h = Image.open(RACINE/'pages'/livre['pages'][0]['img']).size
    pages_html = []
    for i, p in enumerate(livre['pages']):
        dur = ' data-density="hard"' if i == 0 else ''
        pages_html.append(f'<div class="page"{dur} data-rot="{p.get("rot", 0)}">'
                          f'<img src="data:image/webp;base64,{webp(RACINE/"pages"/p["img"])}" alt="{p["nom"]}" decoding="async">'
                          f'<div class="reliure"></div></div>')
    donnees = {
        'titre': livre['titre'], 'sous_titre': livre['sous_titre'],
        'largeur': w, 'hauteur': h,
        'pages': [{'rot': p.get('rot', 0), 'nom': p['nom']} for p in livre['pages']],
        'sommaire': livre['sommaire'],
    }
    html = (ICI/'gabarit.html').read_text(encoding='utf-8')
    mots = livre['titre'].split(' ')
    html = html.replace('{{TITRE_HTML}}', mots[0] + ' <b>' + ' '.join(mots[1:]) + '</b>')
    html = html.replace('{{SOUS_TITRE}}', livre['sous_titre'])
    html = html.replace('{{TITRE}}', livre['titre'])
    html = html.replace('{{POLICE}}', b64(ICI/'polices'/'ArchivoBlack.woff2'))
    html = html.replace('{{PAGEFLIP}}', (ICI/'page-flip.browser.js').read_text(encoding='utf-8'))
    html = html.replace('{{W}}', str(w)).replace('{{H}}', str(h))
    html = html.replace('{{PAGES}}', '\n'.join(pages_html))
    html = html.replace('{{DONNEES}}', json.dumps(donnees, ensure_ascii=False))
    sortie = RACINE/'livre.html'
    sortie.write_text(html, encoding='utf-8')
    print(f'{sortie.name} : {len(livre["pages"])} pages, {sortie.stat().st_size/1e6:.1f} Mo')

if __name__ == '__main__':
    main()
