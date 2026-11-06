"""Redresse chaque photo de page : perspective, lumière, netteté.
Usage : python3 redresser.py [numéros...]   (sans argument : toutes les pages)
Les coins de chaque page sont dans PAGES (coordonnées dans la photo d'origine,
ordre : haut-gauche, haut-droit, bas-droit, bas-gauche ; ils peuvent sortir de la photo)."""
import sys, json, numpy as np, cv2
from pathlib import Path
ICI = Path(__file__).resolve().parent.parent
OUT_W, OUT_H = 1400, 1980          # format A4 portrait

def vline(x0, y0, s):  return ('v', x0, y0, s)   # x = x0 + s*(y-y0)
def hline(x0, y0, s):  return ('h', x0, y0, s)   # y = y0 + s*(x-x0)
def inter(v, h):
    _, vx, vy, vs = v; _, hx, hy, hs = h
    # x = vx + vs*(y-vy) ; y = hy + hs*(x-hx)
    y = (hy + hs*(vx - vs*vy - hx)) / (1 - hs*vs)
    return [vx + vs*(y-vy), y]
def quad(L, T, R, B):
    return [inter(L,T), inter(R,T), inter(R,B), inter(L,B)]

PAGES = {
 '01': dict(q=[[172,112],[1334,95],[1574,1904],[55,1918]], kind='cover'),
 '02': dict(q=quad(vline(72,30,0.006), hline(95,30,-0.004), vline(1372,100,0.094), hline(100,1988,0.0)), kind='front'),
 '03': dict(q=quad(vline(111,100,-0.066), hline(240,50,-0.067), vline(1371,100,0.112), hline(0,1996,0.0146)), kind='back'),
 '04': dict(q=quad(vline(60,0,0.0), hline(0,-5,0.0), vline(1361,100,0.14), hline(0,2012,0.0)), kind='front'),
 '05': dict(q=quad(vline(121,290,-0.052), hline(240,93,-0.144), vline(1360,100,0.0967), hline(0,1990,0.01)), kind='back'),
 '06': dict(q=quad(vline(95,0,-0.012), hline(0,-5,0.0), vline(1435,480,0.125), hline(0,2020,0.0)), kind='front', reg=False),
 '07': dict(q=quad(vline(116,290,-0.073), hline(420,50,-0.052), vline(1359,100,0.119), hline(0,2000,0.0)), kind='back'),
 '08': dict(q=quad(vline(140,0,-0.061), hline(0,-5,0.0), vline(1441,100,0.089), hline(0,2006,0.0)), kind='front'),
 '09': dict(q=quad(vline(132,290,-0.0887), hline(240,82,-0.054), vline(1369,100,0.117), hline(780,1998,0.019)), kind='back6'),  # 6 étapes : autre modèle
}

# Les recettes suivent toutes le même modèle : chaque recto est aligné sur la page 02,
# chaque verso sur la page 03 (repères communs : logo, textes fixes, tableaux).
REF = {'front': '02', 'back': '03'}

def base_matrix(n):
    src = np.float32(PAGES[n]['q']); dst = np.float32([[0,0],[OUT_W,0],[OUT_W,OUT_H],[0,OUT_H]])
    return cv2.getPerspectiveTransform(src, dst)

def apply(im, M):
    out = cv2.warpPerspective(im, M, (OUT_W, OUT_H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    valid = cv2.warpPerspective(np.full(im.shape[:2], 255, np.uint8), M, (OUT_W, OUT_H), flags=cv2.INTER_NEAREST, borderValue=0)
    return out, valid

def register(img, ref):
    """Homographie qui superpose img (déjà redressée grossièrement) sur ref."""
    g1 = cv2.createCLAHE(2.0, (8,8)).apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    g2 = cv2.createCLAHE(2.0, (8,8)).apply(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY))
    sift = cv2.SIFT_create(nfeatures=12000)
    k1, d1 = sift.detectAndCompute(g1, None); k2, d2 = sift.detectAndCompute(g2, None)
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, b in m if a.distance < 0.75*b.distance]
    p1 = np.float32([k1[a.queryIdx].pt for a in good]); p2 = np.float32([k2[a.trainIdx].pt for a in good])
    # on ne garde que des déplacements plausibles (la page est déjà presque droite)
    ok = np.linalg.norm(p1-p2, axis=1) < 140
    H, inl = cv2.findHomography(p1[ok], p2[ok], cv2.RANSAC, 4.0)
    return H, int(inl.sum()), int(ok.sum())

_cache = {}
def warp(n):
    im = cv2.imread(str(ICI/'photos'/f'{n}.jpg'))
    M = base_matrix(n)
    ref = REF.get(PAGES[n]['kind']) if PAGES[n].get('reg', True) else None
    if ref and ref != n:
        if ref not in _cache: _cache[ref] = apply(cv2.imread(str(ICI/'photos'/f'{ref}.jpg')), base_matrix(ref))[0]
        rough, _ = apply(im, M)
        H, nin, ntot = register(rough, _cache[ref])
        print(f'  {n} -> {ref} : {nin}/{ntot} repères communs')
        M = H @ M
    return apply(im, M)

if __name__ == '__main__':
    noms = sys.argv[1:] or sorted(PAGES)
    (ICI/'pages'/'brut').mkdir(parents=True, exist_ok=True)
    for n in noms:
        out, valid = warp(n)
        cv2.imwrite(str(ICI/'pages'/'brut'/f'{n}.png'), out)
        cv2.imwrite(str(ICI/'pages'/'brut'/f'{n}_valide.png'), valid)
        print(n, 'ok', 'hors-photo: %.1f%%' % (100*(valid==0).mean()))
