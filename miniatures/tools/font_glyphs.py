"""Lettres de la police « Atelier Étoile », en images (hauteur de capitale = 1000 px).

Deux sources :
  - les lettres décalquées sur les planches de référence (font/refs/*.png), après redressement de l'arche ;
  - les lettres absentes des planches, construites avec le même vocabulaire (blocs, fentes fines à bouts ronds,
    encoches, petits angles arrondis).
"""
import os
import numpy as np
import cv2
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'font', 'refs')
CAP, PAD = 1000, 260          # hauteur de capitale et marge (accents au-dessus, jambages en dessous)
GAP = 35                      # blanc entre deux lettres, mesuré sur les planches
SW = 34                       # largeur d'une fente
WORDS = {'oublie': 'OUBLIÉ', 'notre-futur': 'NOTREFUTUR', 'lantiheros': 'LANTIHÉROS', 'monstre': 'MONSTRE',
         'dominer': 'DOMINER', 'nous': 'NOUS', 'reve': 'RÊVE', 'pere': 'PÈRE', 'aimer': 'AIMER'}
# largeur relative de chaque planche (certaines ont été étirées) : on ramène tout à la même chasse
XSCALE = {'oublie': 1 / 1.07, 'reve': 1 / 1.12, 'monstre': 1.07}
# le meilleur exemplaire de chaque lettre : (planche, rang dans le mot)
PICK = {'A': ('lantiheros', 1), 'B': ('oublie', 2), 'D': ('dominer', 0), 'E': ('dominer', 5), 'F': ('notre-futur', 5),
        'H': ('lantiheros', 5), 'I': ('dominer', 3), 'L': ('lantiheros', 0), 'M': ('dominer', 2), 'N': ('dominer', 4),
        'O': ('nous', 1), 'P': ('pere', 0), 'R': ('dominer', 6), 'S': ('nous', 3), 'T': ('notre-futur', 2),
        'U': ('nous', 2), 'V': ('reve', 2)}
MARKS = {'acute': ('lantiheros', 6), 'grave': ('pere', 1), 'circumflex': ('reve', 1)}


# ---------------------------------------------------------------- redressement des planches
def unwarp(name, deg=4):
    g = cv2.imread(os.path.join(REFS, name + '.png'), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    H, W = g.shape
    lab, _ = ndi.label(g > .5)
    comps = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        if (lab[sl] == i + 1).sum() < 40:
            continue
        comps.append((i + 1, sl[1].start, sl[1].stop, sl[0].start, sl[0].stop))
    hmax = max(c[4] - c[3] for c in comps)
    main = [c for c in comps if c[4] - c[3] > .6 * hmax]
    xt, yt, xb, yb = [], [], [], []
    for i, x0, x1, y0, y1 in main:
        m = lab[y0:y1, x0:x1] == i
        cols = np.where(m.any(0))[0]
        top = m.argmax(0)[cols] + y0
        bot = (m.shape[0] - 1 - m[::-1].argmax(0)[cols]) + y0
        tol = max(3, .012 * (y1 - y0))
        kt, kb = top <= top.min() + tol, bot >= bot.max() - tol
        xt += list(cols[kt] + x0); yt += list(top[kt]); xb += list(cols[kb] + x0); yb += list(bot[kb])

    def fit(xs, ys, upper):
        xs, ys = np.array(xs, float), np.array(ys, float)
        xn, w = (xs - W / 2) / (W / 2), np.ones(len(ys))
        for _ in range(12):
            p = np.polyfit(xn, ys, deg, w=w)
            r = ys - np.polyval(p, xn)
            w = np.where((r <= 1.5) if upper else (r >= -1.5), 1.0, .02)
        return p
    xn = (np.arange(W) - W / 2) / (W / 2)
    top, bot = np.polyval(fit(xt, yt, True), xn), np.polyval(fit(xb, yb, False), xn)
    x0, x1 = min(c[1] for c in main), max(c[2] for c in main)
    capc = float(np.interp((x0 + x1) / 2, np.arange(W), bot - top)) + 1
    sx = CAP / capc * XSCALE.get(name, 1)
    ox0, ox1 = x0 - 30, x1 + 30
    OW, OH = int((ox1 - ox0) * sx), CAP + 2 * PAD
    u = np.arange(OW) / sx + ox0
    t, b = np.interp(u, np.arange(W), top), np.interp(u, np.arange(W), bot) + 1
    v = (np.arange(OH) - PAD) / CAP
    mapx = np.tile(u.astype(np.float32), (OH, 1))
    mapy = (t[None, :] + v[:, None] * (b - t)[None, :]).astype(np.float32)
    return np.clip(cv2.remap(g, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0), 0, 1)


def segment(name):
    """Renvoie l'image redressée et, pour chaque lettre du mot, sa boîte et ses accents."""
    img = unwarp(name)
    lab, _ = ndi.label(img > .5)
    comps = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        if (lab[sl] == i + 1).sum() < 400:
            continue
        comps.append(dict(i=i + 1, x0=sl[1].start, x1=sl[1].stop, y0=sl[0].start, y1=sl[0].stop))
    main = sorted([c for c in comps if c['y1'] - c['y0'] > .6 * CAP], key=lambda c: c['x0'])
    small = [c for c in comps if c['y1'] - c['y0'] <= .6 * CAP]
    assert len(main) == len(WORDS[name]), name
    for c in main:
        c['marks'] = [s for s in small if s['y1'] < PAD + 60 and s['x0'] < c['x1'] and s['x1'] > c['x0']]
    used = [id(m) for c in main for m in c['marks']]
    extra = [s for s in small if id(s) not in used]
    return img, lab, main, extra


_cache = {}
def _seg(name):
    if name not in _cache:
        _cache[name] = segment(name)
    return _cache[name]


def canvas(w):
    return np.zeros((CAP + 2 * PAD, int(round(w))), np.float32)


def traced(ch):
    name, k = PICK[ch]
    img, lab, main, _ = _seg(name)
    c = main[k]
    out = canvas(c['x1'] - c['x0'])
    m = (lab[:, c['x0']:c['x1']] == c['i'])
    out[:] = np.where(ndi.binary_dilation(m, iterations=3), img[:, c['x0']:c['x1']], 0)
    return out


def traced_mark(kind):
    """L'accent seul, et son décalage horizontal par rapport au bord gauche de sa lettre."""
    name, k = MARKS[kind]
    img, lab, main, _ = _seg(name)
    c = main[k]; s = c['marks'][0]
    out = canvas(s['x1'] - s['x0'])
    m = (lab[:, s['x0']:s['x1']] == s['i'])
    out[:] = np.where(ndi.binary_dilation(m, iterations=3), img[:, s['x0']:s['x1']], 0)
    return out, (s['x0'] + s['x1']) / 2 - (c['x0'] + c['x1']) / 2


def traced_apostrophe():
    img, lab, main, extra = _seg('lantiheros')
    s = extra[0]
    out = canvas(s['x1'] - s['x0'])
    m = (lab[:, s['x0']:s['x1']] == s['i'])
    out[:] = np.where(ndi.binary_dilation(m, iterations=3), img[:, s['x0']:s['x1']], 0)
    return out


# ---------------------------------------------------------------- outils de construction
def Y(y):           # ordonnée « capitale » (0 = haut des capitales, 1000 = ligne de base) vers ligne d'image
    return y + PAD


def poly(img, pts, val=1.0):
    p = np.array([[x, Y(y)] for x, y in pts], np.float64)
    cv2.fillPoly(img, [np.round(p * 16).astype(np.int32)], val, lineType=cv2.LINE_AA, shift=4)


def rect(img, x0, y0, x1, y1, val=1.0):
    poly(img, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], val)


def slit(img, x0, y0, x1, y1, w=SW):
    """Fente à bouts ronds entre deux points (les bouts sont à l'intérieur du segment donné)."""
    d = np.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / d * w / 2, (y1 - y0) / d * w / 2
    a, b = (x0 + ux, Y(y0) + uy), (x1 - ux, Y(y1) - uy)
    cv2.line(img, tuple(np.round(np.array(a) * 16).astype(int)), tuple(np.round(np.array(b) * 16).astype(int)), 0.0, int(round(w)), cv2.LINE_AA, 4)


def cut(img, x0, y0, x1, y1, w=SW):
    """Fente ouverte sur un bord : bout rond en (x1, y1), coupe franche du côté (x0, y0)."""
    d = np.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    nx, ny = -uy * w / 2, ux * w / 2
    ex, ey = x1 - ux * w / 2, y1 - uy * w / 2
    poly(img, [(x0 + nx, y0 + ny), (ex + nx, ey + ny), (ex - nx, ey - ny), (x0 - nx, y0 - ny)], 0.0)
    cv2.circle(img, tuple(np.round(np.array([ex, Y(ey)]) * 16).astype(int)), int(round(w / 2 * 16)), 0.0, -1, cv2.LINE_AA, 4)


def soften(img, r=9.0):
    """Arrondit légèrement tous les angles (flou puis seuil), comme sur les planches."""
    m = int(r * 4)
    b = cv2.GaussianBlur(cv2.copyMakeBorder(img, m, m, m, m, cv2.BORDER_CONSTANT, value=0), (0, 0), r)[m:-m, m:-m]
    return np.clip((b - .5) * 6 + .5, 0, 1)


def resize_w(img, w):
    return cv2.resize(img, (int(round(w)), img.shape[0]), interpolation=cv2.INTER_AREA if w < img.shape[1] else cv2.INTER_CUBIC)


def ink_box(img):
    ys, xs = np.where(img > .5)
    return xs.min(), ys.min() - PAD, xs.max() + 1, ys.max() + 1 - PAD


def holes(img):
    """Masque des creux fermés d'une lettre."""
    ink = img > .5
    outside, _ = ndi.label(~ink)
    border = set(outside[0, :]) | set(outside[-1, :]) | set(outside[:, 0]) | set(outside[:, -1])
    return (~ink) & ~np.isin(outside, list(border))


def fill_holes(img):
    out = img.copy()
    out[ndi.binary_dilation(holes(img), iterations=4)] = 1
    return out
