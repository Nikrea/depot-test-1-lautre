"""Extraction des formes du logo L'AUTRE depuis les visuels sources.

Chaque forme (le L, l'apostrophe, les lettres du wordmark, la phrase manuscrite)
est convertie en champ de distance signée (SDF). Un SDF permet de rendre la forme
nette à n'importe quelle échelle, de la dilater / l'éroder, et de la fusionner
avec d'autres formes comme des gouttes de matière (smooth-min).

Unités :
  - "logo" : pixels de assets/source/logo_lockup.jpg (1254 x 1254)
  - "tag"  : pixels de la phrase manuscrite, suréchantillonnée x4 depuis banner_tagline.jpg
"""
from __future__ import annotations

import heapq
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source")
CACHE = os.path.join(ROOT, "assets", "cache", "shapes.npz")

UP = 4      # suréchantillonnage pour l'extraction
TEX = 2     # texels par unité logo dans les textures SDF
PAD = 230   # marge (unités logo) autour des formes du symbole


# --------------------------------------------------------------------------- outils

def sdf_from_mask(mask: np.ndarray) -> np.ndarray:
    """SDF euclidienne (négative à l'intérieur) d'un masque binaire {0,1}."""
    m = (mask > 0).astype(np.uint8)
    outside = cv2.distanceTransform(1 - m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    inside = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return (outside - inside).astype(np.float32)


def smooth_mask(mask: np.ndarray, sigma: float) -> np.ndarray:
    """Lisse les contours d'un masque (filtre gaussien le long de chaque contour)
    pour effacer le bruit du grain photo sans arrondir la forme globale."""
    m = (mask > 0).astype(np.uint8)
    contours, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    if hier is None:
        return out
    shift = 4
    k = int(3 * sigma) + 1
    g = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    g /= g.sum()
    smoothed = []
    for c in contours:
        pts = c[:, 0, :].astype(np.float64)
        if len(pts) > 2 * k + 3:
            ext = np.concatenate([pts[-k:], pts, pts[:k]])
            xs = np.convolve(ext[:, 0], g, mode="valid")
            ys = np.convolve(ext[:, 1], g, mode="valid")
            pts = np.stack([xs, ys], 1)
        smoothed.append(np.round(pts * (1 << shift)).astype(np.int32).reshape(-1, 1, 2))
    # contours extérieurs (parent == -1) remplis, trous (parent >= 0) vidés
    for i, c in enumerate(smoothed):
        if hier[0][i][3] < 0:
            cv2.fillPoly(out, [c], 1, lineType=cv2.LINE_8, shift=shift)
    for i, c in enumerate(smoothed):
        if hier[0][i][3] >= 0:
            cv2.fillPoly(out, [c], 0, lineType=cv2.LINE_8, shift=shift)
    return out


def crop_texture(sdf_up: np.ndarray, x0: float, y0: float, x1: float, y1: float):
    """Découpe une région (unités logo) d'une SDF suréchantillonnée (x UP) et la
    ré-échantillonne à TEX texels / unité. Retourne (texture, origine)."""
    h, w = sdf_up.shape
    xs0, ys0 = int(round(x0 * UP)), int(round(y0 * UP))
    xs1, ys1 = int(round(x1 * UP)), int(round(y1 * UP))
    canvas = np.full((ys1 - ys0, xs1 - xs0), 1e4, np.float32)
    cx0, cy0 = max(xs0, 0), max(ys0, 0)
    cx1, cy1 = min(xs1, w), min(ys1, h)
    canvas[cy0 - ys0:cy1 - ys0, cx0 - xs0:cx1 - xs0] = sdf_up[cy0:cy1, cx0:cx1]
    # hors image source : on prolonge par la distance au bord (approximation sûre)
    if (cx0, cy0, cx1, cy1) != (xs0, ys0, xs1, ys1):
        yy, xx = np.mgrid[ys0:ys1, xs0:xs1]
        cxx, cyy = np.clip(xx, 0, w - 1), np.clip(yy, 0, h - 1)
        far = sdf_up[cyy, cxx] + np.hypot(xx - cxx, yy - cyy)
        canvas = np.where(canvas >= 1e4, far, canvas).astype(np.float32)
    out_w = int(round((x1 - x0) * TEX))
    out_h = int(round((y1 - y0) * TEX))
    tex = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_AREA) / UP
    return tex.astype(np.float32), np.array([x0, y0], np.float32)


# --------------------------------------------------------------------------- logo

def build_logo(out: dict) -> None:
    img = cv2.imread(os.path.join(SRC, "logo_lockup.jpg")).astype(np.float32)
    g = cv2.GaussianBlur(img[:, :, 1], (0, 0), 1.6)          # canal vert : corps jaune vs halo rouge
    g_up = cv2.resize(g, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    g_up = cv2.GaussianBlur(g_up, (0, 0), 2.0)

    edge = (g_up > 110).astype(np.uint8)    # contour visuel
    core = (g_up > 165).astype(np.uint8)    # noyaux : lettres bien séparées
    n_e, lab_e, st_e, _ = cv2.connectedComponentsWithStats(edge, 8)
    n_c, lab_c, st_c, cen_c = cv2.connectedComponentsWithStats(core, 8)

    comps = []
    for i in range(1, n_c):
        x, y, w, h, a = st_c[i]
        if a < 120 * UP * UP:
            continue
        comps.append(dict(id=i, x=x / UP, y=y / UP, w=w / UP, h=h / UP, area=a / UP / UP,
                          cx=cen_c[i][0] / UP, cy=cen_c[i][1] / UP))
    symbol = [c for c in comps if c["y"] < 800]
    letters = sorted([c for c in comps if c["y"] >= 800], key=lambda c: c["cx"])

    def edge_comp(c):
        return lab_e[int(c["cy"] * UP), int(c["cx"] * UP)]

    # ---- symbole : le L et l'apostrophe sont isolés -> contour direct
    body = max(symbol, key=lambda c: c["area"])
    quote = min(symbol, key=lambda c: c["area"])
    for name, c in (("L", body), ("Q", quote)):
        m = smooth_mask(lab_e == edge_comp(c), sigma=1.5 * UP)
        sdf = sdf_from_mask(m)
        tex, org = crop_texture(sdf, c["x"] - PAD, c["y"] - PAD, c["x"] + c["w"] + PAD, c["y"] + c["h"] + PAD)
        ys, xs = np.nonzero(m)
        out[f"{name}_tex"], out[f"{name}_org"] = tex, org
        out[f"{name}_cen"] = np.array([xs.mean() / UP, ys.mean() / UP], np.float32)
        out[f"{name}_area"] = np.float32(m.sum() / UP / UP)
        evals, evecs = np.linalg.eigh(np.cov(np.stack([xs / UP, ys / UP])))
        out[f"{name}_axis"] = evecs[:, 1].astype(np.float32)
        out[f"{name}_bbox"] = np.array([xs.min(), ys.min(), xs.max(), ys.max()], np.float32) / UP

    # ---- wordmark : les halos fusionnent U-T-R-E au seuil "contour" ->
    # SDF des noyaux, dilatée d'un décalage mesuré sur les lettres isolées (L et A)
    deltas = []
    for c in letters:
        eid = edge_comp(c)
        ids_inside = np.unique(lab_c[(lab_e == eid) & (lab_c > 0)])
        if len(ids_inside) == 1 and c["w"] > 60:      # lettre isolée et assez grande
            em = (lab_e == eid).astype(np.uint8)
            border = em - cv2.erode(em, np.ones((3, 3), np.uint8))
            sdf_core = sdf_from_mask(lab_c == c["id"])
            deltas.append(float(np.median(sdf_core[border > 0])))
    delta = float(np.median(deltas)) if deltas else 5.0 * UP

    word_org, word_cen, word_inr = [], [], []
    for j, c in enumerate(letters):
        eid = edge_comp(c)
        ids_inside = np.unique(lab_c[(lab_e == eid) & (lab_c > 0)])
        if len(ids_inside) == 1 and c["w"] < 60:
            # petite forme isolée (apostrophe + sa goutte) : contour direct
            m = (lab_e == eid)
        else:
            m = sdf_from_mask(lab_c == c["id"]) < delta
        m = smooth_mask(m, sigma=3.6 * UP)
        sdf = sdf_from_mask(m)
        pad = 110
        ys, xs = np.nonzero(m)
        bx0, by0, bx1, by1 = xs.min() / UP, ys.min() / UP, xs.max() / UP, ys.max() / UP
        tex, org = crop_texture(sdf, bx0 - pad, by0 - pad, bx1 + pad, by1 + pad)
        out[f"W{j}_tex"] = tex
        word_org.append(org)
        word_cen.append([xs.mean() / UP, ys.mean() / UP])
        word_inr.append(-float(sdf.min()) / UP)     # rayon inscrit max
    out["W_org"] = np.array(word_org, np.float32)
    out["W_cen"] = np.array(word_cen, np.float32)
    out["W_inr"] = np.array(word_inr, np.float32)
    out["W_n"] = np.int32(len(letters))
    out["W_delta"] = np.float32(delta / UP)


# --------------------------------------------------------------------------- phrase

LINES = {1: ((100, 300), (1330, 60)), 2: ((430, 440), (1700, 230))}   # lignes de base (unités tag)


def _line_frame(line):
    (x0, y0), (x1, y1) = LINES[line]
    u = np.array([x1 - x0, y1 - y0], np.float64)
    u /= np.linalg.norm(u)
    v = np.array([-u[1], u[0]])       # perpendiculaire, vers le bas
    if v[1] < 0:
        v = -v
    return np.array([x0, y0], np.float64), u, v


def build_tagline(out: dict) -> None:
    """Masque de la phrase manuscrite + ordre d'écriture : le tracé est
    squelettisé, chaque trait est parcouru depuis son extrémité la plus en haut
    à gauche, comme une plume, puis les traits s'enchaînent de gauche à droite."""
    from skimage.morphology import skeletonize

    ban = cv2.imread(os.path.join(SRC, "banner_tagline.jpg")).astype(np.float32)
    crop = ban[280:410, 1000:1450]
    lum = crop[:, :, 1] + 0.3 * crop[:, :, 2]
    up = cv2.resize(lum, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    up = cv2.GaussianBlur(up, (0, 0), 2.2)
    hp = up - cv2.GaussianBlur(up, (0, 0), 40)
    tmask = (hp > 30).astype(np.uint8)

    n, lab, st, cen = cv2.connectedComponentsWithStats(tmask, 8)
    keep = np.zeros(n, bool)
    dots = []
    for i in range(1, n):
        a = st[i][4]
        cx, cy = cen[i]
        if a < 10:
            continue
        if 560 < cx < 620 and 170 < cy < 220 and a < 600:   # tache parasite après "L'autre"
            continue
        if a < 60:                                         # points des « i » (moi, toi) : trop fins
            dots.append((cx, cy))
            continue
        keep[i] = True
    tmask = keep[lab].astype(np.uint8)
    for cx, cy in dots:
        cv2.circle(tmask, (int(round(cx * 16)), int(round(cy * 16))), int(5.5 * 16), 1, -1, cv2.LINE_8, shift=4)
    tmask = smooth_mask(tmask, sigma=1.5)
    hh, ww = tmask.shape

    # ligne de chaque composante
    n, lab, st, cen = cv2.connectedComponentsWithStats(tmask, 8)
    comp_line = np.zeros(n, np.int32)
    for i in range(1, n):
        cx, cy = cen[i]
        best, bl = 1e9, 1
        for line, (p, q) in LINES.items():
            yl = p[1] + (cx - p[0]) * (q[1] - p[1]) / (q[0] - p[0])
            if abs(cy - yl) < best:
                best, bl = abs(cy - yl), line
        comp_line[i] = bl

    skel = skeletonize(tmask > 0).astype(np.uint8)
    # chaque pixel de squelette hérite de la composante du tracé qui le contient
    sk_ys, sk_xs = np.nonzero(skel)
    index = -np.ones((hh, ww), np.int64)
    index[sk_ys, sk_xs] = np.arange(len(sk_ys))
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def neighbours(k):
        y, x = sk_ys[k], sk_xs[k]
        for dy, dx in nb:
            yy, xx = y + dy, x + dx
            if 0 <= yy < hh and 0 <= xx < ww and index[yy, xx] >= 0:
                yield index[yy, xx], (1.4142 if dy and dx else 1.0)

    n_sk, lab_sk = cv2.connectedComponents(skel, connectivity=8)
    strokes = []
    for s in range(1, n_sk):
        ks = index[lab_sk == s]
        ks = ks[ks >= 0]
        if len(ks) == 0:
            continue
        line = comp_line[lab[sk_ys[ks[0]], sk_xs[ks[0]]]]
        o, u, v = _line_frame(line)
        pu = (sk_xs[ks] - o[0]) * u[0] + (sk_ys[ks] - o[1]) * u[1]
        pv = (sk_xs[ks] - o[0]) * v[0] + (sk_ys[ks] - o[1]) * v[1]
        deg = np.array([sum(1 for _ in neighbours(k)) for k in ks])
        cand = np.nonzero(deg <= 1)[0]
        if len(cand) == 0:
            cand = np.arange(len(ks))
        score = pu[cand] + 1.6 * pv[cand]       # départ : en haut à gauche
        start = ks[cand[np.argmin(score)]]
        dist = {int(start): 0.0}
        heap = [(0.0, int(start))]
        while heap:
            dcur, k = heapq.heappop(heap)
            if dcur > dist.get(k, 1e18):
                continue
            for k2, w in neighbours(k):
                nd = dcur + w
                if nd < dist.get(int(k2), 1e18):
                    dist[int(k2)] = nd
                    heapq.heappush(heap, (nd, int(k2)))
        strokes.append(dict(line=line, ks=ks, dist=np.array([dist.get(int(k), 0.0) for k in ks]),
                            umin=pu.min(), umax=pu.max(), length=max(dist.values()) if dist else 0.0))

    # enchaînement des traits : vitesse de plume constante + levers de plume
    rel = np.zeros(len(sk_ys), np.float32)
    line_total = {}
    for line in (1, 2):
        ss = sorted([s for s in strokes if s["line"] == line], key=lambda s: s["umin"])
        speed = 1350.0                    # unités tag / s : une plume rapide mais lisible
        tcur, prev = 0.0, None
        small_run = 0
        for s in ss:
            if prev is not None:
                gap = s["umin"] - prev["umax"]
                pause = 0.02                # lever de plume
                if gap > 28:
                    pause += 0.07           # espace entre deux mots
                if prev["length"] < 14 and small_run >= 3:
                    pause += 0.28           # silence après les points de suspension
                tcur += pause
            small_run = small_run + 1 if s["length"] < 14 else 0
            rel[s["ks"]] = tcur + s["dist"] / speed
            tcur += s["length"] / speed + (0.03 if s["length"] < 14 else 0.0)
            prev = s
        line_total[line] = tcur

    # propagation à tous les pixels : pixel de squelette le plus proche
    _, lbl = cv2.distanceTransformWithLabels(1 - skel, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    # cv2 numérote les pixels nuls de l'entrée (= le squelette) dans l'ordre de balayage
    lut_t = np.zeros(lbl.max() + 1, np.float32)
    lut_l = np.zeros(lbl.max() + 1, np.uint8)
    lut_t[1:len(sk_ys) + 1] = rel
    line_of_sk = np.array([comp_line[lab[y, x]] for y, x in zip(sk_ys, sk_xs)], np.uint8)
    lut_l[1:len(sk_ys) + 1] = line_of_sk
    tsdf = sdf_from_mask(tmask)
    out["T_sdf"] = cv2.GaussianBlur(tsdf, (0, 0), 0.8).astype(np.float32)
    out["T_rel"] = lut_t[lbl]
    out["T_line"] = lut_l[lbl]
    out["T_total"] = np.array([line_total[1], line_total[2]], np.float32)
    out["T_size"] = np.array([ww, hh], np.float32)


def build() -> dict:
    out: dict = {}
    build_logo(out)
    build_tagline(out)
    return out


def load(rebuild: bool = False) -> dict:
    if not rebuild and os.path.exists(CACHE):
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    data = build()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, **data)
    return data


if __name__ == "__main__":
    d = load(rebuild=True)
    for k, v in d.items():
        print(k, getattr(v, "shape", ()), v if np.ndim(v) <= 1 and np.size(v) < 16 else "")
