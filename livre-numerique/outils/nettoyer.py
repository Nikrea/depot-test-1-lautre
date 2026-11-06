"""Étape 2 : bords hors page, lumière, couleurs, netteté.  pages/brut/NN.png -> pages/NN.jpg"""
import sys, numpy as np, cv2
from pathlib import Path
from redresser import PAGES
ICI = Path(__file__).resolve().parent.parent

def poly_terms(x, y, deg=3):
    return np.stack([x**i * y**j for i in range(deg+1) for j in range(deg+1-i)], -1)

def paper_light(img):
    """Niveau du papier blanc sur toute la page (enveloppe haute lissée, par canal)."""
    h, w = img.shape[:2]; s = 8
    small = cv2.resize(img, (w//s, h//s), interpolation=cv2.INTER_AREA).astype(float)
    hsv = cv2.cvtColor(small.astype(np.uint8), cv2.COLOR_BGR2HSV)
    yy, xx = np.mgrid[0:small.shape[0], 0:small.shape[1]]
    X = xx/small.shape[1]; Y = yy/small.shape[0]
    cand = (hsv[...,1] < 45) & (hsv[...,2] > 120)
    pts = np.where(cand)
    A = poly_terms(X[pts], Y[pts])
    fits = []
    for c in range(3):
        v = small[...,c][pts]; keep = np.ones(len(v), bool)
        for _ in range(8):                      # on remonte vers le blanc du papier
            coef = np.linalg.lstsq(A[keep], v[keep], rcond=None)[0]
            r = v - A @ coef
            keep = r > -6
        full = poly_terms(*np.meshgrid(np.linspace(0,1,w), np.linspace(0,1,h)))
        fits.append(full @ coef)
    return np.stack(fits, -1)

def outside_mask(img, valid, kind):
    """Zones hors de la page : hors photo d'origine, ou fond sombre collé au bord."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # seul le vrai fond (table noire) compte : le papier dans l'ombre reste, avec son texte
    dark = ((hsv[...,2] < 72) & (hsv[...,1] < 70)).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    h, w = dark.shape; band = np.zeros_like(dark); m = 130
    band[-m:,:] = band[:,-m:] = 1
    if kind != 'front': band[:m,:] = band[:,:m] = 1   # rectos : la photo touche le haut, la reliure est blanchie à part
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark & band)
    out = np.zeros_like(dark)
    for k in range(1, n):
        x, y, ww, hh, a = st[k]
        if (x == 0 or y == 0 or x+ww >= w or y+hh >= h) and a > 150 and hsv[...,2][lab == k].mean() < 55:
            out[lab == k] = 1
    if kind == 'front': out[1500:, :300] = 0        # QR code collé au bord : ce n'est pas du fond
    out |= (valid == 0)
    return cv2.dilate(out, np.ones((7,7), np.uint8))

def unsharp(img, r=1.4, amount=0.55):
    b = cv2.GaussianBlur(img, (0,0), r)
    return cv2.addWeighted(img, 1+amount, b, -amount, 0)

def process(n):
    src = ICI/'pages'/'brut'/f'{n}_titre.png'          # couverture avec le nouveau nom
    img = cv2.imread(str(src if src.exists() else ICI/'pages'/'brut'/f'{n}.png'))
    valid = cv2.imread(str(ICI/'pages'/'brut'/f'{n}_valide.png'), 0)
    kind = PAGES[n]['kind']
    out_m = outside_mask(img, valid, kind) if kind != 'cover' else (valid == 0).astype(np.uint8)
    f = img.astype(float)
    if kind != 'cover':
        light = paper_light(img)
        f = f / np.maximum(light, 40) * 246.0
        # papier : légère teinte chaude, encre plus franche
        f = np.clip(f, 0, 255)
        lo = 18.0
        f = (f - lo) / (246.0 - lo) * 246.0
        f = 255 * (np.clip(f, 0, 255)/255) ** 1.08
        paper = np.array([238, 244, 247], float)          # BGR, papier à peine chaud
        f = f * (paper/246.0)
        # bande de reliure (pli, talon détachable) : on la blanchit
        if kind == 'front': out_m[:1520, :70] = 1        # (le QR code du bas reste intact)
        else: out_m[:, 1366:] = 1
        m = cv2.GaussianBlur(out_m.astype(float), (0,0), 2)[...,None]
        f = f*(1-m) + paper*m
    else:
        f = cv2.inpaint(img, out_m, 6, cv2.INPAINT_TELEA).astype(float)
        f = (f - 6) / (250 - 6) * 255
    f = np.clip(f, 0, 255).astype(np.uint8)
    # couleurs un peu plus vives (photos de plats délavées par l'éclairage)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(float)
    hsv[...,1] = np.clip(hsv[...,1] * (1.18 if kind != 'cover' else 1.08), 0, 255)
    f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    f = unsharp(f)
    cv2.imwrite(str(ICI/'pages'/f'{n}.jpg'), f, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    print(n, 'ok', round((ICI/'pages'/f'{n}.jpg').stat().st_size/1024), 'Ko')

if __name__ == '__main__':
    for n in (sys.argv[1:] or sorted(PAGES)): process(n)
