"""Exporte le livre en PDF et en ePub (pour les apps de lecture du téléphone).
Les fiches recettes, imprimées de côté dans le livret, sont remises à l'endroit.
Usage : python3 outils/exporter.py   ->  livre.pdf, livre.epub"""
import io, json, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image
import img2pdf
from pypdf import PdfReader, PdfWriter

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
LARGEUR_A4_POUCES = 210 / 25.4

def pages_a_l_endroit(livre):
    """(nom, jpeg) de chaque page, tournée pour se lire droite."""
    for p in livre['pages']:
        im = Image.open(RACINE/'pages'/p['img']).convert('RGB')
        rot = p.get('rot', 0)
        if rot == -90: im = im.transpose(Image.ROTATE_90)     # quart de tour vers la gauche
        if rot == 90:  im = im.transpose(Image.ROTATE_270)    # quart de tour vers la droite
        dpi = min(im.size) / LARGEUR_A4_POUCES                  # => page au format A4
        b = io.BytesIO(); im.save(b, 'JPEG', quality=84, optimize=True, progressive=True, dpi=(dpi, dpi))
        yield p, im.size, b.getvalue()

def pdf(livre, pages):
    brut = img2pdf.convert([j for _, _, j in pages])
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(brut)))
    for s in livre['sommaire']:
        w.add_outline_item(s['titre'], s['page'] - 1)
    w.add_metadata({'/Title': livre['titre'], '/Subject': livre['sous_titre']})
    w.page_mode = '/UseOutlines'
    sortie = RACINE/'livre.pdf'
    with open(sortie, 'wb') as f: w.write(f)
    return sortie

def epub(livre, pages):
    """ePub à mise en page fixe : une image par page, on tourne les pages dans Livres (Apple) ou Play Livres."""
    titre = escape(livre['titre'])
    maj = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ident = 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'livre-numerique/' + livre['titre']))
    sortie = RACINE/'livre.epub'
    z = zipfile.ZipFile(sortie, 'w')
    z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    Z = lambda n, s: z.writestr(n, s, compress_type=zipfile.ZIP_DEFLATED)
    Z('META-INF/container.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
      '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    Z('META-INF/com.apple.ibooks.display-options.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<display_options><platform name="*"><option name="fixed-layout">true</option>'
      '<option name="open-to-spread">false</option></platform></display_options>')
    Z('OEBPS/style.css', 'html, body { margin: 0; padding: 0; background: #f6f3ec; }\n'
      'img { position: absolute; left: 0; top: 0; display: block; }\n')
    manifest, spine = [], []
    for i, (p, (w, h), jpg) in enumerate(pages, 1):
        z.writestr(f'OEBPS/images/{i:02d}.jpg', jpg, compress_type=zipfile.ZIP_STORED)
        nom = escape(p['nom'])
        Z(f'OEBPS/p{i:02d}.xhtml', f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="fr" xml:lang="fr">
<head><meta charset="utf-8"/><meta name="viewport" content="width={w}, height={h}"/>
<title>{nom}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body><img src="images/{i:02d}.jpg" alt="{nom}" width="{w}" height="{h}" style="width:{w}px;height:{h}px"/></body>
</html>''')
        prop = ' properties="cover-image"' if i == 1 else ''
        manifest.append(f'<item id="img{i:02d}" href="images/{i:02d}.jpg" media-type="image/jpeg"{prop}/>')
        manifest.append(f'<item id="p{i:02d}" href="p{i:02d}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{i:02d}"/>')
    toc = '\n'.join(f'<li><a href="p{s["page"]:02d}.xhtml">{escape(s["titre"])}</a></li>' for s in livre['sommaire'])
    Z('OEBPS/nav.xhtml', f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="fr" xml:lang="fr">
<head><meta charset="utf-8"/><title>Sommaire</title></head>
<body>
<nav epub:type="toc" id="toc"><h1>Sommaire</h1><ol>
{toc}
</ol></nav>
<nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="cover" href="p01.xhtml">Couverture</a></li></ol></nav>
</body>
</html>''')
    Z('OEBPS/content.opf', f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="fr"
         prefix="rendition: http://www.idpf.org/vocab/rendition/#">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{ident}</dc:identifier>
<dc:title>{titre}</dc:title>
<dc:language>fr</dc:language>
<dc:description>{escape(livre["sous_titre"])}</dc:description>
<meta property="dcterms:modified">{maj}</meta>
<meta property="rendition:layout">pre-paginated</meta>
<meta property="rendition:orientation">auto</meta>
<meta property="rendition:spread">none</meta>
<meta name="cover" content="img01"/>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="css" href="style.css" media-type="text/css"/>
{chr(10).join(manifest)}
</manifest>
<spine>
{chr(10).join(spine)}
</spine>
</package>''')
    z.close()
    return sortie

def main():
    livre = json.loads((RACINE/'livre.json').read_text(encoding='utf-8'))
    pages = list(pages_a_l_endroit(livre))
    for f in (pdf(livre, pages), epub(livre, pages)):
        print(f'{f.name} : {f.stat().st_size/1e6:.1f} Mo')

if __name__ == '__main__':
    main()
