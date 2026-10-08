"""Étape 4 : une marionnette par personne (calque RGBA + profondeur), prête à être animée.

- ordre de profondeur (médiane de Depth Anything) : on dessine du fond vers l'avant ;
- « corps caché » : ce qui est derrière les voisins plus proches, ou sous le bord du cadre, est
  complété (silhouette rang par rang, buste prolongé à la largeur des épaules) puis rempli par diffusion de la
  couleur de la personne + texture de son propre vêtement (carrés recollés au hasard), pour qu'on
  ne voie pas de trou quand elle se lève ;
- bords décontaminés (couleur du sujet propagée sous le liseré) pour éviter les halos de décor ;
- yeux lumineux repérés (centres) pour le halo et les « regards qui restent ».

Sorties : assets/layers/p<i>.png (RGBA), p<i>_z.png (profondeur 16 bits), puppets.json
"""
import glob
import json
import math
import os

import cv2
import numpy as np
from scipy.ndimage import binary_fill_holes, median_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source", "selfie.png")
LAY = os.path.join(ROOT, "assets", "layers")
PAD_B = 560          # marge sous le cadre où l'on prolonge les corps


def push_pull(img, known, levels=9):
    """Remplit les pixels inconnus par pyramide « push-pull » (moyenne pondérée des pixels connus)."""
    w = known.astype(np.float32)
    c = img.astype(np.float32) * (w[..., None] if img.ndim == 3 else w)
    ws, cs = [w], [c]
    for _ in range(levels):
        if min(ws[-1].shape[:2]) < 4:
            break
        ws.append(cv2.pyrDown(ws[-1]))
        cs.append(cv2.pyrDown(cs[-1]))
    div = lambda cc, ww: cc / (np.maximum(ww, 1e-6)[..., None] if cc.ndim == 3 else np.maximum(ww, 1e-6))
    est = div(cs[-1], ws[-1])
    for l in range(len(ws) - 2, -1, -1):
        h, wd = ws[l].shape[:2]
        up = cv2.pyrUp(est, dstsize=(wd, h))
        a = np.clip(ws[l] * 3, 0, 1)
        if est.ndim == 3:
            a = a[..., None]
        est = a * div(cs[l], ws[l]) + (1 - a) * up
    out = img.astype(np.float32).copy()
    out[~known] = est[~known]
    return out


def amodal_span(m, occ, win=41, taper=0.07):
    """Silhouette « complète » du sujet : pour chaque rang, l'étendue [gauche, droite] du visible
    (lissée par médiane glissante). À partir de la ligne d'épaules (le rang le plus large de la moitié
    basse), le buste descend à cette largeur en s'affinant à peine.
    On ne remplit que là où le sujet peut être caché (voisin plus proche, ou sous le cadre)."""
    HP, W = m.shape
    rows = np.nonzero(m.any(1))[0]
    ytop, ybot = rows.min(), rows.max()
    L = np.full(HP, np.nan)
    R = np.full(HP, np.nan)
    for y in rows:
        xs = np.nonzero(m[y])[0]
        L[y], R[y] = xs.min(), xs.max()
    idx = np.arange(ytop, ybot + 1)
    ok = ~np.isnan(L[idx])
    Li = median_filter(np.interp(idx, idx[ok], L[idx][ok]), win, mode="nearest")
    Ri = median_filter(np.interp(idx, idx[ok], R[idx][ok]), win, mode="nearest")
    wid = median_filter(Ri - Li, 61, mode="nearest")
    lo = int(0.3 * len(idx))
    ks = lo + int(np.argmax(wid[lo:]))
    ys, Ls, Rs = idx[ks], Li[ks], Ri[ks]
    ws = Rs - Ls
    span = np.zeros_like(m)
    xx = np.arange(W)
    for y in range(ytop, HP):
        k = y - ytop
        if y < ys:
            a, b = Li[k], Ri[k]
        else:
            t = min((y - ys) / 400.0, 1.0)
            a, b = Ls + taper * ws * t, Rs - taper * ws * t
            if y <= ybot:
                a, b = min(a, Li[k]), max(b, Ri[k])
        span[y] = (xx >= a) & (xx <= b)
    am = span & (m | occ)
    # on ne garde que ce qui est relié au visible, et on arrondit les angles
    k, cc = cv2.connectedComponents(am.astype(np.uint8))
    keep = np.unique(cc[m & am])
    am = np.isin(cc, keep[keep > 0])
    am = cv2.GaussianBlur(am.astype(np.float32), (0, 0), 6) > 0.5
    am = (am & (m | occ)) | m
    # bouche les petits jours (fentes de décor entre deux corps) pour un buste d'un seul tenant
    am = cv2.morphologyEx(am.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 1), np.uint8)) > 0
    return binary_fill_holes(am)


def fabric_detail(src_p, m, eyes, need, rng, P=48):
    """Texture du vêtement pour les parties inventées : des carrés de détail fin (passe-haut) pris au
    hasard dans la bande de vêtement sous le menton, recollés en fondu enchaîné (fenêtres de Hann)
    — une maille, des plis, sans motif répété ni symétrie."""
    HP, W = m.shape
    hp = src_p - cv2.GaussianBlur(src_p, (0, 0), 5)
    rows = np.nonzero(m.any(1))[0]
    if len(eyes) == 2:
        d = math.hypot(eyes[0][0] - eyes[1][0], eyes[0][1] - eyes[1][1])
        y_cut = max(e[1] for e in eyes) + 2.2 * d
    else:
        y_cut = rows.min() + 0.45 * (rows.max() - rows.min())
    C = m.copy()
    C[: int(y_cut)] = False
    out = np.zeros_like(hp)
    for size in (P + 1, P // 2 + 1):
        ok = cv2.erode(C.astype(np.uint8), np.ones((size, size), np.uint8)) > 0
        cy, cx = np.nonzero(ok)
        if len(cy) > 20:
            break
    else:
        return out
    win = np.outer(np.hanning(P), np.hanning(P)).astype(np.float32)[..., None] + 1e-3
    wsum = np.zeros((HP, W, 1), np.float32)
    half = P // 2
    for y in range(-half, HP, half):
        for x in range(-half, W, half):
            ya, xa = max(y, 0), max(x, 0)
            yb, xb = min(y + P, HP), min(x + P, W)
            if yb <= ya or xb <= xa or not need[ya:yb, xa:xb].any():
                continue
            k = rng.integers(len(cy))
            sy = int(np.clip(cy[k] - half, 0, HP - P))
            sx = int(np.clip(cx[k] - half, 0, W - P))
            patch = hp[sy:sy + P, sx:sx + P]
            out[ya:yb, xa:xb] += (patch * win)[ya - y:yb - y, xa - x:xb - x]
            wsum[ya:yb, xa:xb] += win[ya - y:yb - y, xa - x:xb - x]
    # la moyenne de carrés indépendants adoucit le grain : on lui rend son contraste
    return 1.35 * out / np.maximum(wsum, 1e-3)


def main():
    src = cv2.imread(SRC).astype(np.float32)
    H, W = src.shape[:2]
    lab = cv2.imread(os.path.join(LAY, "labels.png"), 0)
    depth = cv2.imread(os.path.join(LAY, "depth.png"), -1).astype(np.float32) / 65535
    n = int(lab.max())
    med = [float(np.median(depth[lab == i + 1])) for i in range(n)]
    order = list(np.argsort(med))  # du fond vers l'avant
    rank = {int(p): r for r, p in enumerate(order)}

    HP = H + PAD_B
    lab_p = np.zeros((HP, W), np.uint8)
    lab_p[:H] = lab
    src_p = np.zeros((HP, W, 3), np.float32)
    src_p[:H] = src
    dep_p = np.zeros((HP, W), np.float32)
    dep_p[:H] = depth
    below = np.zeros((HP, W), bool)
    below[H:] = True

    # yeux lumineux : petites taches claires et peu saturées (chapeau haut-de-forme morphologique)
    lum = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    tophat = lum - cv2.morphologyEx(lum, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    sat = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_BGR2HSV)[..., 1]
    glow = ((tophat > 45) & (lum > 120) & (sat < 90)).astype(np.uint8)
    k, cc, st, cen = cv2.connectedComponentsWithStats(glow)
    spots = [(float(tophat[cc == c].sum()), cen[c]) for c in range(1, k)]
    rng = np.random.default_rng(5)
    meta = {"W": W, "H": H, "pad_b": PAD_B, "order": [int(o) for o in order], "people": {}}
    disk = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

    for i in range(n):
        m = lab_p == i + 1
        closer = np.isin(lab_p, [j + 1 for j in range(n) if rank[j] > rank[i]])
        occ = closer | below
        body = amodal_span(m, occ)

        # couleur : pixels visibles du sujet (légèrement érodés = décontaminés), le reste diffusé
        core = cv2.erode(m.astype(np.uint8), disk(2)) > 0
        rgb = push_pull(src_p, core)
        # texture du vêtement prolongée, lumière qui baisse doucement en s'éloignant du visible
        mys, mxs = np.nonzero(m[:H])
        mine = [(sc, c) for sc, c in spots if lab[int(c[1]), int(c[0])] == i + 1]
        eyes = [[float(c[0]), float(c[1]), sc] for sc, c in sorted(mine, key=lambda t: -t[0])[:2]]
        dist = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
        shade = (0.70 + 0.30 * np.exp(-dist / 320.0))[..., None]
        inv = ~core
        det = fabric_detail(src_p, m, eyes, body & inv, rng)
        fade = (0.35 + 0.65 * np.exp(-dist / 450.0))[..., None]
        rgb[inv] = (rgb * shade + det * fade)[inv]
        # bords du sujet : on garde l'original à l'intérieur, la couleur propagée sur le liseré
        rgb[core] = src_p[core]

        a = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 0.8)
        a[~cv2.dilate(body.astype(np.uint8), disk(2)).astype(bool)] = 0
        z = push_pull(dep_p, m & (dep_p > 0))

        ys, xs = np.nonzero(a > 0.01)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        rgba = np.dstack([rgb, a[..., None] * 255]).clip(0, 255).astype(np.uint8)[y0:y1, x0:x1]
        cv2.imwrite(os.path.join(LAY, f"p{i}.png"), rgba)
        zz = z[y0:y1, x0:x1]
        cv2.imwrite(os.path.join(LAY, f"p{i}_z.png"), (zz.clip(0, 1) * 65535).astype(np.uint16))

        meta["people"][str(i)] = {
            "bbox": [int(x0), int(y0), int(x1), int(y1)],
            "depth": med[i],
            "rank": rank[i],
            "center": [float(mxs.mean()), float(mys.mean())],
            "top": int(mys.min()),
            "eyes": eyes,
        }
        print(f"p{i}: rang {rank[i]} prof {med[i]:.2f} bbox {x0},{y0}-{x1},{y1} yeux {len(eyes)}")

    with open(os.path.join(LAY, "puppets.json"), "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
