"""Extrait la photo du plat de chaque recette, à l'endroit, sans papier ni texte autour,
et la retouche (bruit, lumière, couleurs, netteté).  ->  recompose/photos/NNN.jpg"""
import cv2, numpy as np
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
SORTIE = ICI/'recompose'/'photos'

# Pages déjà redressées par redresser.py (pages/brut/NN.png) : cadre de la photo, page tournée à l'endroit.
ANCIENNES = {204: ('04', (40, 258, 1525, 1215)), 205: ('06', (40, 262, 1530, 1250)),
             206: ('08', (40, 265, 1530, 1222)), 251: ('02', (40, 262, 1525, 1205))}
# Nouvelles photos : 4 coins de la zone photo dans la photo d'origine, puis cadre final.
NOUVELLES = {225: ('10', [(265, 48), (1245, 30), (1268, 1448), (178, 1448)], (140, 40, 1425, 922)),
             234: ('12', [(288, 62), (1228, 52), (1228, 1528), (196, 1520)], (150, 75, 1422, 965)),
             245: ('14', [(222, 30), (1282, 30), (1278, 1468), (212, 1466)], (12, 92, 1422, 1000))}

def a_l_endroit(n, coins):
    im = cv2.imread(str(ICI/'photos'/f'{n}.jpg')); W, H = 1060, 1430
    M = cv2.getPerspectiveTransform(np.float32(coins), np.float32([[0, 0], [W, 0], [W, H], [0, H]]))
    out = cv2.warpPerspective(im, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    return cv2.rotate(out, cv2.ROTATE_90_COUNTERCLOCKWISE)

def retoucher(img):
    img = cv2.fastNlMeansDenoisingColored(img, None, 4, 5, 7, 21)          # grain de la photo du papier
    f = img.astype(np.float32); nive = f.copy()                              # niveaux : noirs et blancs plus francs
    for c in range(3):
        lo, hi = np.percentile(f[..., c], (0.3, 99.7))
        nive[..., c] = (f[..., c] - lo) / max(hi - lo, 1) * 255
    img = np.clip(f * 0.5 + nive * 0.5, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.08, 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    flou = cv2.GaussianBlur(img, (0, 0), 1.0)
    return cv2.addWeighted(img, 1.3, flou, -0.3, 0)

def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    for num, (n, (x0, y0, x1, y1)) in ANCIENNES.items():
        page = cv2.rotate(cv2.imread(str(ICI/'pages'/'brut'/f'{n}.png')), cv2.ROTATE_90_COUNTERCLOCKWISE)
        cv2.imwrite(str(SORTIE/f'{num}.jpg'), retoucher(page[y0:y1, x0:x1]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    for num, (n, coins, (x0, y0, x1, y1)) in NOUVELLES.items():
        cv2.imwrite(str(SORTIE/f'{num}.jpg'), retoucher(a_l_endroit(n, coins)[y0:y1, x0:x1]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    for f in sorted(SORTIE.glob('*.jpg')):
        print(f.name, cv2.imread(str(f)).shape[1::-1])

if __name__ == '__main__':
    main()
