"""Couverture : remplace « NICOLAS » par un autre nom, dans le style du titre « HELLO ».
pages/brut/01.png -> pages/brut/01_titre.png"""
import sys, numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ICI = Path(__file__).resolve().parent.parent
POLICE = str(Path(__file__).resolve().parent/'polices'/'ArchivoBlack.ttf')
NOM = sys.argv[1] if len(sys.argv) > 1 else "L’ANTIHÉROS"

# Géométrie mesurée sur la couverture redressée (px)
X0, CAP_TOP, BASE = 138, 324, 413        # début de ligne, haut et bas des capitales de « NICOLAS »
PENTE = -0.006                            # le titre monte très légèrement vers la droite
SX, GRAS, ESPACE = 0.76, 4, 8             # condensation, engraissement (px), espace entre lettres
SS = 4                                    # sur-échantillonnage du rendu

def lettre(ch, cap):
    ft = ImageFont.truetype(POLICE, 400); b = ft.getbbox('H'); hcap = b[3]-b[1]
    size = (cap - 2*GRAS) * SS * 400 / hcap
    ft = ImageFont.truetype(POLICE, int(size)); bH = ft.getbbox('H')
    W, H = int(size*1.6), int(size*2.0); oy = H*0.4
    im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).text((W*0.15, oy), ch, font=ft, fill=255)
    a = np.asarray(im).astype(np.float32)/255
    a = cv2.resize(a, (int(W*SX), H), interpolation=cv2.INTER_AREA)
    a = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*GRAS*SS+1,)*2))
    top = oy + bH[1] - GRAS*SS                      # haut des capitales dans ce rendu
    cols = np.where(a.max(0) > 0.02)[0]
    return a[:, cols.min():cols.max()+1], top

def mot(texte, cap):
    """Masque (sur-échantillonné) du mot, aligné sur le haut des capitales."""
    approches = {"L’": -int(0.24*cap*SS), "’A": -int(0.10*cap*SS)}   # l'apostrophe se loge contre le L
    gs = [lettre(c, cap) for c in texte]
    ref = max(t for _, t in gs); H = max(g.shape[0] for g, _ in gs) + 200
    W = sum(g.shape[1] for g, _ in gs) + ESPACE*SS*len(gs) + 200
    out = np.zeros((H, W), np.float32); x = 0
    for i, (g, t) in enumerate(gs):
        dy = int(round(ref - t)); h = min(g.shape[0], H-dy)
        out[dy:dy+h, x:x+g.shape[1]] = np.maximum(out[dy:dy+h, x:x+g.shape[1]], g[:h])
        x += g.shape[1] + ESPACE*SS + approches.get(texte[i:i+2], 0)
    return out[:, :x], ref

def fond_vert(img, masque):
    """Reconstruit le vert de la couverture sous l'ancien texte : dégradé lissé + grain du papier."""
    h, w = img.shape[:2]
    y0, y1, x0, x1 = 290, 440, 100, 1380
    zone = img[y0:y1, x0:x1].astype(np.float32)
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    vert = (hsv[...,2] < 140) & (masque[y0:y1, x0:x1] == 0)
    vert = cv2.erode(vert.astype(np.uint8), np.ones((5,5), np.uint8)) > 0
    yy, xx = np.mgrid[0:y1-y0, 0:x1-x0]; X = xx/(x1-x0); Y = yy/(y1-y0)
    T = lambda X, Y: np.stack([np.ones_like(X), X, Y, X*X, X*Y, Y*Y, X**3, X*X*Y], -1)
    A = T(X[vert], Y[vert]); lisse = np.zeros_like(zone)
    for c in range(3):
        coef = np.linalg.lstsq(A, zone[...,c][vert], rcond=None)[0]
        lisse[...,c] = T(X, Y) @ coef
    # grain : pris dans le vert propre à droite du titre, répété en miroir
    src = img[300:430, 760:1300].astype(np.float32)
    grain = src - cv2.GaussianBlur(src, (0,0), 5)
    gh, gw = grain.shape[:2]
    tile = np.concatenate([grain, grain[:, ::-1]], 1); tile = np.concatenate([tile, tile[::-1]], 0)
    reps = (int(np.ceil((y1-y0)/tile.shape[0])), int(np.ceil((x1-x0)/tile.shape[1])), 1)
    g = np.tile(tile, reps)[:y1-y0, :x1-x0]
    full = img.astype(np.float32).copy()
    full[y0:y1, x0:x1] = lisse + g
    return full, (y0, y1, x0, x1)

def main():
    img = cv2.imread(str(ICI/'pages'/'brut'/'01.png'))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    blanc = ((hsv[...,2] > 125) & (hsv[...,1] < 80)).astype(np.uint8)
    ancien = np.zeros_like(blanc); ancien[308:426, 118:705] = blanc[308:426, 118:705]
    ancien = cv2.dilate(ancien, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13,13)))
    # couleur des lettres, relative au vert qui les entoure
    coeur = cv2.erode(blanc[300:430, 118:705], np.ones((9,9), np.uint8)) > 0
    lettres = img[300:430, 118:705][coeur].astype(np.float32)
    fond, (y0, y1, x0, x1) = fond_vert(img, cv2.dilate(blanc, np.ones((9,9), np.uint8)))
    ratio = np.percentile(lettres, 70, 0) / np.median(fond[300:430, 118:705][coeur], 0)
    m = ancien.astype(np.float32); m = cv2.GaussianBlur(m, (0,0), 2)[..., None]
    out = img.astype(np.float32)*(1-m) + fond*m

    # nouveau nom
    cap = BASE - CAP_TOP
    a, ref = mot(NOM, cap)
    a = cv2.resize(a, (a.shape[1]//SS, a.shape[0]//SS), interpolation=cv2.INTER_AREA)
    ref /= SS
    canvas = np.zeros(img.shape[:2], np.float32)
    ty = int(round(CAP_TOP - ref)); h, w = a.shape
    w = min(w, canvas.shape[1]-X0)
    canvas[ty:ty+h, X0:X0+w] = a[:, :w]
    # légère inclinaison comme l'original, puis le même flou de photo
    M = cv2.getRotationMatrix2D((X0, BASE), np.degrees(np.arctan(-PENTE))*-1, 1.0)
    canvas = cv2.warpAffine(canvas, M, canvas.shape[::-1])
    canvas = cv2.GaussianBlur(canvas, (0,0), 1.25)[..., None]
    encre = np.clip(cv2.GaussianBlur(fond, (0,0), 8) * ratio, 0, 255)   # grain du vert non amplifié
    grain = (out - cv2.GaussianBlur(out, (0,0), 5)) * 0.12
    out = out*(1-canvas) + (encre + grain)*canvas
    out = np.clip(out, 0, 255).astype(np.uint8)
    cv2.imwrite(str(ICI/'pages'/'brut'/'01_titre.png'), out)
    largeur = np.where(canvas[..., 0].max(0) > 0.1)[0]
    print('titre posé :', NOM, '| x', largeur.min(), '->', largeur.max())

if __name__ == '__main__':
    main()
