"""Fabrique la police « Atelier Étoile » (font/AtelierEtoile.otf et .woff2) à partir des planches de référence.

    pip install numpy opencv-python-headless scipy fonttools potracer brotli
    python3 miniatures/tools/build_font.py            # écrit la police et font/specimen.png

Lettres décalquées : A B D E F H I L M N O P R S T U V, accents aigu, grave, circonflexe, apostrophe.
Lettres construites dans le même style : C G J K Q W X Y Z, chiffres, ponctuation, tréma, cédille, Œ, Æ.
"""
import os, sys
import numpy as np
import cv2
import potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import font_glyphs as G
from font_glyphs import CAP, PAD, GAP, SW, poly, rect, slit, cut, soften, resize_w, traced, fill_holes, canvas

ST = 213            # largeur d'un fût
UNITS = 700 / CAP   # 1000 px de capitale = 700 unités de police (cadratin de 1000)
OUT = os.path.join(G.ROOT, 'font')


# ---------------------------------------------------------------- lettres construites
def o_outer(w=445):
    return resize_w(fill_holes(traced('O')), w)


def o_plain(w=445):
    o = o_outer(w)
    slit(o, w / 2, 184, w / 2, 818)
    return o


def g_c(w=455):
    o = o_plain(w)
    cut(o, w + 8, 500, w / 2 - 6, 500, 64)
    return o


def g_g(w=468):
    o = o_outer(w)
    x = w * .51
    slit(o, x, 187, x, 500, 40)
    rect(o, x - 20, 400, x + 20, 585, 0.0)        # la fente descend droit jusqu'à l'ergot…
    rect(o, x - 2, 585, x + 20, 720, 0.0)         # …puis se resserre (marche nette, comme sur « MENSONGE »)
    slit(o, x + 9, 690, x + 9, 751, 22)
    cut(o, w + 8, 379, x - 6, 379, 52)
    return o


def g_q(w=455):
    o = o_plain(w)
    poly(o, [(w * .50, 850), (w * .74, 850), (w * 1.0, 1095), (w * .76, 1095)])
    return o


def g_j(w=420):
    u = resize_w(traced('U'), w)
    xs = int(w * 214 / 461)
    u[:G.Y(640), :xs] = 0
    return u


def g_w():
    return traced('M')[::-1].copy()   # M retourné : même dessin, tête en bas


def _flip_v(img):
    out = canvas(img.shape[1])
    out[PAD:PAD + CAP] = img[PAD:PAD + CAP][::-1]
    return out


def g_k(w=480):
    o = canvas(w); rect(o, 0, 0, w, CAP)
    poly(o, [(ST, -6), (ST + 58, -6), (ST + 14, 455), (ST, 455)], 0.0)
    poly(o, [(ST, CAP + 6), (ST + 58, CAP + 6), (ST + 14, 545), (ST, 545)], 0.0)
    poly(o, [(w + 6, 395), (w + 6, 605), (w - 150, 500)], 0.0)
    return o


def g_x(w=480):
    o = canvas(w); rect(o, 0, 0, w, CAP)
    poly(o, [(w / 2 - 32, -6), (w / 2 + 32, -6), (w / 2, 395)], 0.0)
    poly(o, [(w / 2 - 32, CAP + 6), (w / 2 + 32, CAP + 6), (w / 2, 605)], 0.0)
    poly(o, [(-6, 405), (-6, 595), (125, 500)], 0.0)
    poly(o, [(w + 6, 405), (w + 6, 595), (w - 125, 500)], 0.0)
    return o


def g_y(w=480):
    o = canvas(w); h = ST / 2 + 4
    poly(o, [(0, 0), (w, 0), (w, 430), (w / 2 + h, 705), (w / 2 + h, CAP), (w / 2 - h, CAP), (w / 2 - h, 705), (0, 430)])
    poly(o, [(w / 2 - 30, -6), (w / 2 + 30, -6), (w / 2, 430)], 0.0)
    return o


def g_z(w=430):
    o = canvas(w); rect(o, 0, 0, w, CAP)
    poly(o, [(-6, 200), (w * .53, 200), (-6, 650)], 0.0)
    poly(o, [(w + 6, 800), (w * .47, 800), (w + 6, 350)], 0.0)
    return o


def d_1(w=300):
    o = canvas(w)
    poly(o, [(0, 205), (112, 0), (w, 0), (w, CAP), (87, CAP), (87, 310), (0, 310)])
    return o


def d_2(w=430):
    o = g_z(w)
    o[:G.Y(330)] *= o_outer(w)[:G.Y(330)] > .5
    return o


def d_3(w=420):
    e = resize_w(traced('E'), w)[:, ::-1].copy()
    m = o_outer(w) > .5
    e[:, w // 2:] *= m[:, w // 2:]
    poly(e, [(w + 6, 440), (w + 6, 515), (w - 28, 477)], 0.0)
    return e


def d_4(w=462):
    o = canvas(w)
    rect(o, 0, 0, w, 770); rect(o, w - ST, 0, w, CAP)
    cut(o, w - ST - (w - 2 * ST) / 2, -8, w - ST - (w - 2 * ST) / 2, 575, w - 2 * ST)
    return o


def d_5(w=440):
    s = resize_w(traced('S'), w)
    rect(s, 0, 0, w, 120)
    return s


def d_6(w=440):
    o = o_outer(w)
    slit(o, w / 2, 545, w / 2, 818)
    slit(o, w / 2, 184, w / 2, 425)
    cut(o, w + 8, 400, w / 2 - 6, 400, 50)
    return o


def d_7(w=420):
    o = canvas(w)
    poly(o, [(0, 0), (w, 0), (w, 255), (w * .69, CAP), (w * .17, CAP), (w * .47, 225), (0, 225)])
    return o


def d_8(w=440):
    o = o_outer(w)
    slit(o, w / 2, 184, w / 2, 428); slit(o, w / 2, 572, w / 2, 818)
    poly(o, [(-6, 462), (-6, 538), (24, 500)], 0.0); poly(o, [(w + 6, 462), (w + 6, 538), (w - 24, 500)], 0.0)
    return o


def d_9(w=440):
    return _flip_v(d_6(w))[:, ::-1].copy()


DOT = 215
def p_period():
    o = canvas(DOT); rect(o, 0, CAP - DOT, DOT, CAP); return o


def p_comma():
    o = canvas(DOT)
    poly(o, [(0, CAP - DOT), (DOT, CAP - DOT), (DOT, CAP), (125, 1165), (22, 1165), (78, CAP), (0, CAP)])
    return o


def p_exclam():
    o = canvas(DOT); poly(o, [(0, 0), (DOT, 0), (DOT - 22, 700), (22, 700)]); rect(o, 0, CAP - DOT, DOT, CAP); return o


def p_question(w=420):
    o = canvas(w); c = w / 2; h = ST / 2
    rect(o, 0, 0, w, 225); rect(o, w - ST, 0, w, 560); rect(o, 0, 0, ST - 20, 335)
    rect(o, c - h, 430, w, 560); rect(o, c - h, 430, c + h, 700)
    o[:G.Y(330)] *= o_outer(w)[:G.Y(330)] > .5
    rect(o, c - h, CAP - DOT, c + h, CAP)
    return o


def p_colon():
    o = canvas(DOT); rect(o, 0, 330, DOT, 330 + DOT); rect(o, 0, CAP - DOT, DOT, CAP); return o


def p_semicolon():
    o = p_comma(); rect(o, 0, 330, DOT, 330 + DOT); return o


def p_dash(w):
    def f():
        o = canvas(w); rect(o, 0, 415, w, 585); return o
    return f


def p_ellipsis():
    w = DOT * 3 + GAP * 2; o = canvas(w)
    for k in range(3):
        rect(o, k * (DOT + GAP), CAP - DOT, k * (DOT + GAP) + DOT, CAP)
    return o


def p_quote():
    a = G.traced_apostrophe(); w = a.shape[1] * 2 + GAP; o = canvas(w)
    o[:, :a.shape[1]] = a; o[:, w - a.shape[1]:] = a
    return o


def p_slash(w=400):
    o = canvas(w); poly(o, [(w - 190, -40), (w, -40), (190, CAP + 40), (0, CAP + 40)]); return o


def p_plus(w=500):
    o = canvas(w); rect(o, 0, 415, w, 585); rect(o, w / 2 - 85, 250, w / 2 + 85, 750); return o


def m_dieresis():
    w = 300; o = canvas(w); rect(o, 0, -165, 125, -40); rect(o, w - 125, -165, w, -40); return o


def m_cedilla():
    w = 200; o = canvas(w)
    poly(o, [(60, 985), (150, 985), (150, 1050), (w, 1050), (w, 1165), (20, 1165), (20, 1085), (60, 1085)])
    return o


def fuse(a, b, overlap=20):
    """Deux lettres collées (Œ, Æ)."""
    w = a.shape[1] + b.shape[1] - overlap; o = canvas(w)
    o[:, :a.shape[1]] = a
    o[:, w - b.shape[1]:] = np.maximum(o[:, w - b.shape[1]:], b)
    return o


CONSTRUCTED = {'C': g_c, 'G': g_g, 'J': g_j, 'K': g_k, 'Q': g_q, 'X': g_x, 'Y': g_y, 'Z': g_z,
               '0': lambda: o_plain(430), '1': d_1, '2': d_2, '3': d_3, '4': d_4, '5': d_5, '6': d_6, '7': d_7, '8': d_8, '9': d_9,
               '.': p_period, ',': p_comma, '!': p_exclam, '?': p_question, ':': p_colon, ';': p_semicolon,
               '-': p_dash(300), '–': p_dash(430), '—': p_dash(640), '…': p_ellipsis, '"': p_quote, '/': p_slash, '+': p_plus}
ROUND = 9.0     # arrondi des angles des lettres construites, calé sur les planches
ACCENTED = {'À': ('A', 'grave'), 'Â': ('A', 'circumflex'), 'Ä': ('A', 'dieresis'), 'É': ('E', 'acute'), 'È': ('E', 'grave'),
            'Ê': ('E', 'circumflex'), 'Ë': ('E', 'dieresis'), 'Î': ('I', 'circumflex'), 'Ï': ('I', 'dieresis'),
            'Ô': ('O', 'circumflex'), 'Ö': ('O', 'dieresis'), 'Ù': ('U', 'grave'), 'Û': ('U', 'circumflex'), 'Ü': ('U', 'dieresis'),
            'Ÿ': ('Y', 'dieresis'), 'Ç': ('C', 'cedilla')}


def all_glyphs():
    g = {}
    for ch in G.PICK:
        g[ch] = traced(ch)
    g['O'] = o_plain(g['O'].shape[1])            # sur les planches, le O porte toujours l'étoile : ici, sa fente seule
    g['W'] = _flip_v(g['M'])
    for ch, fn in CONSTRUCTED.items():
        img = fn()
        g[ch] = soften(img, ROUND) if ch not in ('5', '3', 'J') else soften(img, 4)
    g["'"] = G.traced_apostrophe(); g['’'] = g["'"]
    marks = {}
    for k in G.MARKS:
        marks[k] = G.traced_mark(k)
    marks['dieresis'] = (soften(m_dieresis(), ROUND), 0)
    marks['cedilla'] = (soften(m_cedilla(), ROUND), 0)
    for ch, (base, mk) in ACCENTED.items():
        b, (m, dx) = g[base], marks[mk]
        w = max(b.shape[1], m.shape[1] + 2 * abs(int(dx)))
        o = canvas(w); bx = (w - b.shape[1]) // 2
        o[:, bx:bx + b.shape[1]] = b
        mx = int(round(w / 2 + dx - m.shape[1] / 2)); mx = max(0, min(w - m.shape[1], mx))
        o[:, mx:mx + m.shape[1]] = np.maximum(o[:, mx:mx + m.shape[1]], m)
        g[ch] = o
    g['Œ'] = fuse(g['O'], g['E'], 60); g['Æ'] = fuse(g['A'], g['E'], 30)
    return g


# ---------------------------------------------------------------- vectorisation et police
SIDE = {"'": 16, '’': 16, '"': 16}     # blanc supplémentaire de chaque côté (px), pour que l'apostrophe respire


def outline(img, side=0):
    """Contours de Bézier (unités de police, y vers le haut) d'une lettre en image."""
    b = cv2.GaussianBlur(img, (0, 0), 1.6) > .5
    ys, xs = np.where(b); x0 = xs.min()
    pl = potrace.Bitmap(~b).trace(  # la bibliothèque inverse : on lui donne le fond
        turdsize=30, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=1.0, opticurve=True, opttolerance=.35)
    def P(p):
        return ((p.x - x0 + side) * UNITS + GAP / 2 * UNITS, (PAD + CAP - p.y) * UNITS)
    contours = []
    for c in pl:
        rec = RecordingPen(); rec.moveTo(P(c.start_point))
        for s in c.segments:
            if s.is_corner:
                rec.lineTo(P(s.c)); rec.lineTo(P(s.end_point))
            else:
                rec.curveTo(P(s.c1), P(s.c2), P(s.end_point))
        rec.closePath()
        pts = [P(c.start_point)] + [P(s.end_point) for s in c.segments]
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2
        contours.append((rec, area, pts))
    # orientation : les contours extérieurs dans un sens, les creux dans l'autre
    out = []
    for rec, area, pts in contours:
        px, py = pts[0]
        depth = sum(1 for r2, a2, p2 in contours if r2 is not rec and abs(a2) > abs(area) and cv2.pointPolygonTest(np.array(p2, np.float32), (float(px), float(py)), False) > 0)
        want_pos = depth % 2 == 0
        out.append((rec, (area > 0) != want_pos))
    width = (xs.max() + 1 - x0 + GAP + 2 * side) * UNITS
    return out, width


NAMES = {' ': 'space', "'": 'quotesingle', '’': 'quoteright', '.': 'period', ',': 'comma', '!': 'exclam', '?': 'question', ':': 'colon',
         ';': 'semicolon', '-': 'hyphen', '–': 'endash', '—': 'emdash', '…': 'ellipsis', '"': 'quotedbl', '/': 'slash', '+': 'plus'}
def gname(ch):
    if ch in NAMES: return NAMES[ch]
    if ch.isdigit(): return ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'][int(ch)]
    return ch if ch.isascii() else 'uni%04X' % ord(ch)


def build():
    glyphs = all_glyphs()
    order, cmap, cs, metrics = ['.notdef', 'space'], {32: 'space', 0xA0: 'space'}, {}, {'.notdef': (350, 0), 'space': (int(150 * UNITS + .5), 0)}
    for name in ('.notdef', 'space'):
        cs[name] = T2CharStringPen(metrics[name][0], None).getCharString()
    for ch in sorted(glyphs):
        n = gname(ch); contours, width = outline(glyphs[ch], SIDE.get(ch, 0))
        pen = T2CharStringPen(int(round(width)), None)
        for rec, rev in contours:
            rec.replay(ReverseContourPen(pen) if rev else pen)
        cs[n] = pen.getCharString(); metrics[n] = (int(round(width)), int(round((GAP / 2 + SIDE.get(ch, 0)) * UNITS)))
        order.append(n); cmap[ord(ch)] = n
        if ch.isalpha() and ch.lower() != ch and len(ch.lower()) == 1:
            cmap[ord(ch.lower())] = n          # les minuscules donnent les mêmes capitales
    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order); fb.setupCharacterMap(cmap)
    fb.setupCFF('AtelierEtoile-Regular', {'FullName': 'Atelier Etoile'}, cs, {})
    fb.setupHorizontalMetrics(metrics)
    asc, desc = 880, -140
    fb.setupHorizontalHeader(ascent=asc, descent=desc)
    fb.setupNameTable({'familyName': 'Atelier Etoile', 'styleName': 'Regular'})
    fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc, usWinAscent=asc, usWinDescent=-desc, sCapHeight=700, sxHeight=700)
    fb.setupPost()
    # crénage de l'apostrophe : après un L, elle se pose au-dessus du pied, au milieu du vide entre le fût du L
    # et le flanc incliné du A qui suit ; devant un A, la lettre se rapproche (son haut est en retrait)
    ink = lambda g: np.where((g > .5).any(0))[0]
    row = lambda g, y: np.where(g[PAD + y] > .5)[0]
    L, A, Q = glyphs['L'], glyphs['A'], glyphs["'"]
    wl, wq, side = ink(L).max() + 1, ink(Q).max() + 1, SIDE["'"]
    stem = row(L, 300).max() + 1                       # bord droit du fût du L
    a_in = row(A, int(np.where((Q > .5).any(1))[0].max() - PAD) // 2).min()   # retrait du A à mi-hauteur de l'apostrophe
    q0 = (stem + wl + GAP + a_in) / 2 - wq / 2         # position de l'apostrophe, depuis le bord gauche du L
    k1 = int(round((q0 - (wl + GAP + side)) * UNITS))
    k2 = int(round(((wl + GAP) - (q0 + wq) - GAP - side) * UNITS))
    fea = 'languagesystem DFLT dflt; languagesystem latn dflt;\nfeature kern {\n'
    for q in ('quotesingle', 'quoteright'):
        fea += f'  pos L {q} {k1};\n  pos {q} [A uni00C0 uni00C2 uni00C4 uni00C6] {k2};\n'
    fea += '} kern;\n'
    addOpenTypeFeaturesFromString(fb.font, fea)
    print('crénage L-apostrophe', k1, 'apostrophe-A', k2, '| apostrophe', wq, 'px de large pour 1000 de capitale')
    os.makedirs(OUT, exist_ok=True)
    fb.save(os.path.join(OUT, 'AtelierEtoile.otf'))
    fb.font.flavor = 'woff2'; fb.font.save(os.path.join(OUT, 'AtelierEtoile.woff2'))
    print('glyphes', len(order), 'woff2', os.path.getsize(os.path.join(OUT, 'AtelierEtoile.woff2')), 'octets')
    return glyphs


def specimen(glyphs, path, rows=("ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "0123456789 .,!?:;-–…'\"/+", "ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ")):
    sc = .16; lines = []
    for row in rows:
        tiles = [cv2.resize(glyphs[c], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if c != ' ' else np.zeros((int((CAP + 2 * PAD) * sc), 24), np.float32) for c in row]
        gap = np.zeros((tiles[0].shape[0], int(GAP * sc)), np.float32)
        line = np.concatenate([np.concatenate([t, gap], 1) for t in tiles], 1)
        lines.append(line)
    w = max(l.shape[1] for l in lines)
    img = np.concatenate([np.pad(l, ((0, 0), (0, w - l.shape[1]))) for l in lines], 0)
    cv2.imwrite(path, (np.clip(img, 0, 1) * 255).astype(np.uint8))


def embed():
    """Réécrit la police embarquée dans index.html (entre les marqueurs POLICE et FIN-POLICE)."""
    import base64, re
    page = os.path.join(G.ROOT, 'index.html')
    b64 = base64.b64encode(open(os.path.join(OUT, 'AtelierEtoile.woff2'), 'rb').read()).decode()
    html = open(page, encoding='utf-8').read()
    face = "/*POLICE*/@font-face { font-family: 'Atelier Etoile'; src: url(data:font/woff2;base64," + b64 + ") format('woff2'); font-display: block; }/*FIN-POLICE*/"
    new, n = re.subn(r'/\*POLICE\*/.*?/\*FIN-POLICE\*/', lambda m: face, html, count=1, flags=re.S)
    if n:
        open(page, 'w', encoding='utf-8').write(new); print('police embarquée dans index.html')


if __name__ == '__main__':
    g = build()
    specimen(g, os.path.join(OUT, 'specimen.png'))
    embed()
