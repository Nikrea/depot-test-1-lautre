"""L'AUTRE — intro de chaîne (motion design procédural).

Scénario (9,6 s) :
  1. L'ÉTINCELLE  — dans le noir, un battement de cœur allume une lumière floue,
                    vivante comme une cellule. À droite, à la plume de lumière :
                    « L'autre c'est moi, / l'autre… c'est toi. »
  2. LA MISE AU POINT — bascule de point (rack focus) : la phrase se perd dans le
                    flou, la lumière se précise et prend la forme du L.
  3. LA DIVISION  — un bourgeon de lumière se détache du L : l'apostrophe naît
                    de la même matière. L'autre, c'est moi.
  4. LE NOM       — la caméra recule, L'AUTRE se remplit de lumière, lettre à lettre.
  5. L'EXTINCTION — la lumière refroidit (jaune → orange → rouge) et s'éteint.

Usage :
  python3 intro/render.py --res 1080              # rend toutes les images
  python3 intro/render.py --res 540 --times 1,4.5  # planche de prévisualisation
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from multiprocessing import Pool

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets  # noqa: E402

cv2.setNumThreads(1)

FPS = 24
DURATION = 9.6

# ----------------------------------------------------------------- timeline (s)
T_IGNITE = (0.20, 1.70)
BEATS = (0.50, 2.02, 3.66)
LINE1 = (0.75, 2.00)
LINE2 = (2.15, 3.65)
TEXT_OUT = (3.90, 4.75)
RACK = (3.85, 4.85)
# progression de la caméra : plan 1 (lumière à gauche) -> lockup final
CAM_KEYS = ((3.70, 0.0), (4.35, 0.30), (5.00, 0.62), (5.60, 0.74), (6.40, 0.93), (7.30, 1.0))
MORPH = (3.80, 5.00)
BUD = (4.05, 4.80)
STRETCH = (4.70, 5.16)
WORD = 5.95
WORD_STAGGER = 0.07
WORD_GROW = 0.55
FADE = (8.65, 9.40)


# ----------------------------------------------------------------- easing
def clamp01(x):
    return min(max(x, 0.0), 1.0)


def seg(t, a, b):
    return clamp01((t - a) / (b - a))


def smooth(x):
    return x * x * (3 - 2 * x)


def ease_io3(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_io5(x):
    return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2


def ease_out3(x):
    return 1 - (1 - x) ** 3


def ease_in3(x):
    return x ** 3


def ease_out_back(x, s=1.6):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_io_sine(x):
    return -(math.cos(math.pi * x) - 1) / 2


def lerp(a, b, t):
    return a + (b - a) * t


def pchip(t, keys):
    """Interpolation cubique monotone (Fritsch-Carlson) entre clés (t, valeur)."""
    ks = np.asarray(keys, np.float64)
    x, y = ks[:, 0], ks[:, 1]
    if t <= x[0]:
        return float(y[0])
    if t >= x[-1]:
        return float(y[-1])
    h = np.diff(x)
    dlt = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(x) - 1):
        if dlt[i - 1] * dlt[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dlt[i - 1] + w2 / dlt[i])
    i = int(np.searchsorted(x, t) - 1)
    u = (t - x[i]) / h[i]
    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    return float(h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1])


def spring(tau, zeta=0.5, omega=15.0):
    """Réponse indicielle d'un ressort sous-amorti (0 -> 1, avec dépassement)."""
    if tau <= 0:
        return 0.0, 0.0
    wd = omega * math.sqrt(1 - zeta ** 2)
    e = math.exp(-zeta * omega * tau)
    x = 1 - e * (math.cos(wd * tau) + zeta * omega / wd * math.sin(wd * tau))
    v = e * (omega ** 2 / wd) * math.sin(wd * tau)
    return x, v


def pulse(tau, attack=0.018, decay=0.16):
    if tau <= 0:
        return 0.0
    return (1 - math.exp(-tau / attack)) * math.exp(-tau / decay)


def heartbeat(t):
    """Enveloppe « lub-dub » des battements de cœur."""
    return sum(pulse(t - b) + 0.55 * pulse(t - b - 0.23) for b in BEATS)


# ----------------------------------------------------------------- géométrie
DATA = None
GEO = {}


def init_data():
    global DATA
    if DATA is not None:
        return
    DATA = assets.load()
    d = DATA
    aL, aQ = float(d["L_area"]), float(d["Q_area"])
    cL, cQ = d["L_cen"].astype(np.float64), d["Q_cen"].astype(np.float64)
    GEO["orb_c"] = (cL * aL + cQ * aQ) / (aL + aQ)
    GEO["orb_r"] = math.sqrt((aL + aQ) / math.pi)
    lb, qb = d["L_bbox"], d["Q_bbox"]
    sym = np.array([min(lb[0], qb[0]), min(lb[1], qb[1]), max(lb[2], qb[2]), max(lb[3], qb[3])])
    GEO["sym_c"] = np.array([(sym[0] + sym[2]) / 2, (sym[1] + sym[3]) / 2])
    w_lo = d["W_org"] + 110.0
    w_hi = np.array([d["W_org"][j] + np.array(d[f"W{j}_tex"].shape[::-1]) / assets.TEX - 110.0
                     for j in range(int(d["W_n"]))])
    lock = np.array([min(sym[0], w_lo[:, 0].min()), sym[1], max(sym[2], w_hi[:, 0].max()), w_hi[:, 1].max()])
    GEO["lock_c"] = np.array([(lock[0] + lock[2]) / 2, (lock[1] + lock[3]) / 2])
    GEO["lock_h"] = lock[3] - lock[1]
    GEO["sym_h"] = sym[3] - sym[1]
    # bourgeon : l'apostrophe démarre à moitié dans l'épaule droite du L
    GEO["bud_from"] = np.array([600.0, 445.0])
    GEO["bud_mid"] = np.array([668.0, 442.0])
    GEO["bud_snap"] = np.array([735.0, 440.0])
    GEO["Q_cen"] = cQ
    GEO["Q_axis_angle"] = math.atan2(d["Q_axis"][1], d["Q_axis"][0])


# ----------------------------------------------------------------- caméra
def camera(t):
    """Retourne (C, Z, rot) : point logo au centre de l'écran, zoom en px/unité
    (référence 1080p) et rotation (rad)."""
    W, H = 1920.0, 1080.0

    def center_for(anchor, screen_frac, Z, rot):
        s = np.array([screen_frac[0] * W - W / 2, screen_frac[1] * H - H / 2])
        c, sn = math.cos(rot), math.sin(rot)
        off = np.array([c * s[0] + sn * s[1], -sn * s[0] + c * s[1]]) / Z
        return np.asarray(anchor, np.float64) - off

    # plan 1 : la lumière à gauche, légère poussée
    z1 = lerp(1.60, 1.80, ease_io_sine(seg(t, 0.0, 4.2)))
    r1 = lerp(-0.035, -0.022, seg(t, 0.0, 3.7))
    C1 = center_for(GEO["orb_c"], (0.285, 0.515), z1, r1)
    # plan final : le lockup symbole + wordmark
    z3 = 0.50 * H / GEO["lock_h"]
    C3 = center_for(GEO["lock_c"], (0.5, 0.5), z3, 0.0)

    p = pchip(t, CAM_KEYS)
    C = lerp(C1, C3, p)
    logZ = lerp(math.log(z1), math.log(z3), p)
    rot = lerp(r1, 0.0, smooth(clamp01(p / 0.7)))
    # respiration de mise au point (focus breathing) + lente poussée finale
    Z = math.exp(logZ) * (1 + 0.012 * math.sin(math.pi * seg(t, *RACK)))
    Z *= 1 + 0.035 * ease_io_sine(seg(t, 6.2, DURATION))
    return C, Z, rot


# ----------------------------------------------------------------- état des formes
def spring_from(tau, y0, v0, zeta, omega):
    """Ressort sous-amorti vers 0 depuis (y0, v0) : retourne (y, y')."""
    wd = omega * math.sqrt(1 - zeta ** 2)
    a = zeta * omega
    b = (v0 + a * y0) / wd
    e = math.exp(-a * tau)
    c, s_ = math.cos(wd * tau), math.sin(wd * tau)
    y = e * (y0 * c + b * s_)
    dy = e * (-a * (y0 * c + b * s_) + (-y0 * wd * s_ + b * wd * c))
    return y, dy


def shape_state(t):
    """Paramètres d'animation du symbole à l'instant t.

    Chorégraphie de l'apostrophe :
      BUD      un bourgeon gonfle dans l'épaule du L
      STRETCH  il est tiré lentement : le pont de matière s'étire et s'amincit
      RELEASE  le pont cède, la goutte file à sa place sur un ressort et se balance
    """
    st = {}
    st["morph"] = ease_io3(seg(t, *MORPH))
    hb = heartbeat(t)
    st["orb_r"] = GEO["orb_r"] * (1 + 0.025 * hb + 0.012 * math.sin(2 * math.pi * 0.31 * t))
    st["wobble"] = 16.0 * (1 - st["morph"])

    M, B, F = GEO["bud_mid"], GEO["bud_snap"], GEO["Q_cen"]
    rot0 = math.radians(28)
    g = ease_io3(seg(t, *BUD))
    pos = lerp(GEO["bud_from"], M, g)
    sc = lerp(0.45, 0.78, g)
    rot = rot0
    stretch = 1.0
    k = 80.0
    D = STRETCH[1] - STRETCH[0]
    if t > STRETCH[0]:
        u = seg(t, *STRETCH)
        sp = u * u * (1.6 - 0.6 * u)                 # traction lente, qui accélère puis tient
        pos = lerp(M, B, sp)
        sc = lerp(0.78, 0.88, sp)
        stretch = 1 + 0.24 * sp
        k = lerp(80.0, 30.0, u ** 0.8)
    if t > STRETCH[1]:
        tau = t - STRETCH[1]
        v0 = (1.4 / D) * np.linalg.norm(B - M) / np.linalg.norm(F - B)
        y, dy = spring_from(tau, -1.0, v0, zeta=0.42, omega=14.0)
        x = 1.0 + y
        pos = lerp(B, F, x)
        sc = lerp(0.88, 1.0, clamp01(x))
        rot = rot0 * (1 - x)
        stretch = 1 + 0.24 * math.exp(-7.0 * tau) * math.cos(2 * math.pi * 4.2 * tau)
        k = 30.0 * (1 - smooth(seg(t, STRETCH[1], STRETCH[1] + 0.30)))
    st["Q_pos"] = pos
    st["Q_scale"] = sc
    st["Q_stretch"] = stretch
    move = F - M
    st["Q_dir"] = math.atan2(move[1], move[0])
    st["Q_rot"] = rot
    st["k"] = k
    # recul élastique du L après la séparation
    tau = t - SNAP_T if SNAP_T is not None else -1
    st["L_scale"] = 1 + (0.012 * math.exp(-4.5 * tau) * math.sin(2 * math.pi * 3.2 * tau) if tau > 0 else 0.0)
    return st


SNAP_T = None


# ----------------------------------------------------------------- SDF
def affine_screen_to_logo(C, Z, rot, W, H, S):
    """Matrice 2x3 : pixel écran -> coordonnées logo."""
    Zs = Z * S
    c, s = math.cos(rot), math.sin(rot)
    a = np.array([[c / Zs, s / Zs], [-s / Zs, c / Zs]])
    b = np.array(C) - a @ np.array([W / 2 - 0.5, H / 2 - 0.5])
    return np.hstack([a, b[:, None]])


def compose(A2, A1):
    """A2 ∘ A1 pour des affines 2x3."""
    M1 = np.vstack([A1, [0, 0, 1]])
    M2 = np.vstack([A2, [0, 0, 1]])
    return (M2 @ M1)[:2]


def tex_affine(org):
    return np.array([[assets.TEX, 0, -org[0] * assets.TEX], [0, assets.TEX, -org[1] * assets.TEX]], np.float64)


def sample(tex, M, W, H, interp=cv2.INTER_LINEAR, border=1e4):
    return cv2.warpAffine(tex, M.astype(np.float64), (W, H), flags=interp | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def smin(a, b, k):
    if k <= 1e-3:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def q_local_affine(st):
    """Affine logo -> repère local de l'apostrophe (texture d'origine)."""
    phi = st["Q_dir"]
    sp, sn = st["Q_stretch"], 1.0 / math.sqrt(max(st["Q_stretch"], 1e-3))
    Rphi = np.array([[math.cos(phi), -math.sin(phi)], [math.sin(phi), math.cos(phi)]])
    Dinv = np.diag([1 / sp, 1 / sn])
    th = st["Q_rot"]
    Rinv = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])
    Minv = (Rinv @ Rphi @ Dinv @ Rphi.T) / st["Q_scale"]
    b = GEO["Q_cen"] - Minv @ st["Q_pos"]
    return np.hstack([Minv, b[:, None]]), st["Q_scale"] * math.sqrt(sp * sn)


def l_local_affine(st):
    s = st["L_scale"]
    c = DATA["L_cen"].astype(np.float64)
    return np.hstack([np.eye(2) / s, (c - c / s)[:, None]]), s


def symbol_sdf(t, st, A_logo, W, H, need_orb=True):
    d = DATA
    out = None
    m = st["morph"]
    if m > 0:
        AL, sL = l_local_affine(st)
        dL = sample(d["L_tex"], compose(tex_affine(d["L_org"]), compose(AL, A_logo)), W, H) * sL
        AQ, sQ = q_local_affine(st)
        dQ = sample(d["Q_tex"], compose(tex_affine(d["Q_org"]), compose(AQ, A_logo)), W, H) * sQ
        out = smin(dL, dQ, st["k"])
    if m < 1 and need_orb:
        xs = np.arange(W, dtype=np.float32) + 0.5
        ys = np.arange(H, dtype=np.float32) + 0.5
        X = (A_logo[0, 0] * xs[None, :] + A_logo[0, 1] * ys[:, None] + A_logo[0, 2] - GEO["orb_c"][0]).astype(np.float32)
        Y = (A_logo[1, 0] * xs[None, :] + A_logo[1, 1] * ys[:, None] + A_logo[1, 2] - GEO["orb_c"][1]).astype(np.float32)
        mag, ang = cv2.cartToPolar(X, Y)
        w = st["wobble"]
        wob = (0.55 * np.sin(2 * ang + 1.3 * t + 0.4) + 0.35 * np.sin(3 * ang - 0.9 * t + 2.1)
               + 0.22 * np.sin(5 * ang + 1.7 * t + 4.0)) * w
        orb = mag - st["orb_r"] - wob
        out = orb if out is None else (1 - m) * orb + m * out
    return out


def find_snap_time():
    """Instant où le pont de matière entre le L et l'apostrophe se rompt."""
    W = H = 260
    for i in range(0, 1200):
        t = STRETCH[0] + i / 1000.0
        st = shape_state(t)
        st["morph"] = 1.0
        # petite fenêtre logo entre le L et l'apostrophe
        A = np.array([[1.0, 0, 540.0], [0, 1.0, 320.0]])
        dd = symbol_sdf(t, st, A, W, H, need_orb=False)
        inside = (dd < 0).astype(np.uint8)
        n, _ = cv2.connectedComponents(inside, connectivity=8)
        if n - 1 >= 2:
            return t
    return STRETCH[1]


# ----------------------------------------------------------------- lumière
def build_lut():
    knots = np.array([
        [0.000, 0, 0, 0], [0.020, 16, 3, 0], [0.050, 34, 7, 1], [0.100, 62, 15, 1],
        [0.180, 98, 26, 2], [0.280, 135, 40, 2], [0.400, 185, 64, 1], [0.520, 222, 96, 2],
        [0.640, 248, 135, 5], [0.760, 254, 165, 15], [0.880, 254, 186, 30], [1.000, 254, 197, 42],
        [1.200, 255, 210, 72], [1.500, 255, 226, 120], [2.000, 255, 240, 180], [3.000, 255, 250, 228],
        [6.000, 255, 255, 252]], np.float64)
    e = np.linspace(0, 6, 6001)
    lut = np.stack([np.interp(e, knots[:, 0], knots[:, c]) for c in (1, 2, 3)], 1) / 255.0
    g = np.exp(-0.5 * (np.arange(-18, 19) / 6.0) ** 2)
    g /= g.sum()
    pad = np.pad(lut, ((18, 18), (0, 0)), mode="edge")
    lut = np.stack([np.convolve(pad[:, c], g, mode="valid") for c in range(3)], 1)
    return lut.astype(np.float32)


LUT = None


def tonemap(E):
    idx = np.clip(E * 1000.0, 0, 6000).astype(np.int32)
    return LUT[idx]


def shape_emission(d_units, px_per_unit, edge_level=0.80, inner_w=9.0, halo=(0.24, 7.0, 0.13, 30.0)):
    """Profil lumineux calqué sur la photo du logo : bord net orange, cœur jaune,
    halo rouge à deux échelles."""
    d_px = d_units * px_per_unit
    cov = np.clip(0.5 - d_px, 0.0, 1.0)
    x = np.clip(-d_units / inner_w, 0.0, 1.0)
    inner = edge_level + (1 - edge_level) * x * x * (3 - 2 * x)
    dp = np.maximum(d_units, 0.0)
    h = halo[0] * np.exp(-dp / halo[1]) + halo[2] * np.exp(-dp / halo[3])
    return cov * inner + (1.0 - cov) * h, cov


def disc_kernel(r):
    n = int(math.ceil(r)) + 1
    y, x = np.mgrid[-n:n + 1, -n:n + 1].astype(np.float32)
    k = np.clip(r + 0.5 - np.sqrt(x * x + y * y), 0, 1)
    k = cv2.GaussianBlur(k, (0, 0), max(0.35 * r * 0.25, 0.5))
    return k / k.sum()


def defocus(img, R):
    """Flou d'objectif (disque) de rayon R px, calculé à résolution réduite."""
    if R < 0.6:
        return img
    H, W = img.shape
    f = max(1, int(R // 5))
    small = cv2.resize(img, (max(W // f, 8), max(H // f, 8)), interpolation=cv2.INTER_AREA) if f > 1 else img
    out = cv2.filter2D(small, -1, disc_kernel(R / f), borderType=cv2.BORDER_CONSTANT)
    if f > 1:
        out = cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR)
    return out


# ----------------------------------------------------------------- phrase manuscrite
TREV = None


def build_trev():
    d = DATA
    rel, line, tot = d["T_rel"], d["T_line"], d["T_total"]
    trev = np.full(rel.shape, 99.0, np.float32)
    for li, (a, b) in ((1, LINE1), (2, LINE2)):
        m = line == li
        trev[m] = a + rel[m] * ((b - a) / tot[li - 1])
    return trev


def text_layer(t, W, H, S):
    """Phrase manuscrite, rendue dans sa zone de l'image (ROI). Le halo est un
    flou de l'écriture déjà tracée, pour qu'il suive la plume sans arête."""
    if t > TEXT_OUT[1] + 0.05 or t < LINE1[0] - 0.05:
        return None
    d = DATA
    tw, th = (float(v) for v in d["T_size"])
    out_k = ease_io3(seg(t, *TEXT_OUT))
    width = 0.31 * 1920 * S * (1 + 0.06 * out_k)
    k = width / tw                                     # px écran par unité tag
    cx = (0.715 * 1920 - 14 * seg(t, 0, 3.8) + 70 * ease_io3(seg(t, RACK[0] - 0.1, TEXT_OUT[1]))) * S
    cy = 0.50 * 1080 * S
    R = 26.0 * S * ease_io3(seg(t, *RACK))
    margin = int(40 * S + 1.5 * R) + 4
    x0 = max(int(cx - tw / 2 * k) - margin, 0)
    x1 = min(int(cx + tw / 2 * k) + margin, W)
    y0 = max(int(cy - th / 2 * k) - margin, 0)
    y1 = min(int(cy + th / 2 * k) + margin, H)
    rw, rh = x1 - x0, y1 - y0
    # écran (dans la ROI) -> tag
    A = np.array([[1 / k, 0, tw / 2 - (cx - x0) / k], [0, 1 / k, th / 2 - (cy - y0) / k]])
    dT = sample(d["T_sdf"], A, rw, rh) + 1.4           # +1.4 : trait affiné
    tr = sample(TREV, A, rw, rh, interp=cv2.INTER_NEAREST, border=99.0)
    age = t - tr
    rev = np.clip(age / 0.035, 0.0, 1.0)
    hot = np.exp(-np.maximum(age, 0.0) / 0.16) * rev
    cov = np.clip(0.5 - dT * k, 0.0, 1.0) * rev
    body = cov * (0.84 + 1.5 * hot)
    glow = 0.55 * cv2.GaussianBlur(body, (0, 0), 2.2 * S) + 0.30 * cv2.GaussianBlur(body, (0, 0), 7.0 * S)
    E = body + glow * (1.0 - cov)
    E *= 1.0 - ease_in3(seg(t, TEXT_OUT[0], TEXT_OUT[1]))
    return defocus(E, R), x0, y0


# ----------------------------------------------------------------- wordmark
def word_layer(t, A_logo, W, H, Zs):
    d = DATA
    if t < WORD - 0.05:
        return None
    n = int(d["W_n"])
    body = None
    halo_sum = None
    for j in range(n):
        tau = t - (WORD + j * WORD_STAGGER)
        if tau <= 0:
            continue
        x = clamp01(tau / WORD_GROW)
        ero = float(d["W_inr"][j]) * 1.03 * (1 - ease_out_back(x, 1.7))
        dy = 16.0 * (1 - ease_out3(clamp01(tau / 0.7)))
        vis = smooth(clamp01(tau / 0.14))
        hot = 1 + 0.9 * math.exp(-tau / 0.22)
        Aoff = np.array([[1.0, 0, 0], [0, 1.0, -dy]])
        M = compose(tex_affine(d["W_org"][j]), compose(Aoff, A_logo))
        dj = sample(d[f"W{j}_tex"], M, W, H) + ero
        E, cov = shape_emission(dj, Zs)
        b = cov * E * vis * hot
        hl = (1 - cov) * E * vis * hot
        body = b if body is None else np.maximum(body, b)
        halo_sum = hl if halo_sum is None else halo_sum + hl
    if body is None:
        return None
    return body + halo_sum * np.clip(1 - body, 0, 1)


# ----------------------------------------------------------------- poussières
RNG_P = np.random.default_rng(7)
N_DUST = 34
DUST = dict(
    x=RNG_P.uniform(-0.05, 1.05, N_DUST), y=RNG_P.uniform(-0.05, 1.05, N_DUST),
    z=RNG_P.uniform(0.15, 0.75, N_DUST), vx=RNG_P.normal(0, 0.006, N_DUST),
    vy=RNG_P.uniform(-0.018, -0.004, N_DUST), ph=RNG_P.uniform(0, 6.28, N_DUST),
    b=RNG_P.uniform(0.4, 1.0, N_DUST),
)


def dust_layer(t, C, Z, W, H, S, light_xy, gain):
    """Poussières en suspension, hors du plan de netteté (bokeh), éclairées par la lumière."""
    sw, sh = W // 4, H // 4
    img = np.zeros((sh, sw), np.float32)
    C0, Z0, _ = camera(0.0)
    for i in range(N_DUST):
        z = DUST["z"][i]
        par = (1.0 - z) * 0.9
        px = (DUST["x"][i] + DUST["vx"][i] * t + 0.004 * math.sin(0.7 * t + DUST["ph"][i])) * 1920
        py = (DUST["y"][i] + DUST["vy"][i] * t) * 1080
        px -= (C[0] - C0[0]) * Z * par * 0.35
        py -= (C[1] - C0[1]) * Z * par * 0.35
        px, py = px % 2000 - 40, py % 1160 - 40
        r = (4.0 + 30.0 * (1.0 - z)) * S / 4
        dist = math.hypot(px - light_xy[0], py - light_xy[1]) / 1920
        lit = math.exp(-dist / 0.30)
        e = 0.16 * DUST["b"][i] * lit * gain * min(1.0, 10.0 / (r * 4 / S + 2))
        if e < 0.002:
            continue
        cv2.circle(img, (int(px * S / 4 * 16), int(py * S / 4 * 16)), max(int(r * 16), 8), float(e), -1,
                   lineType=cv2.LINE_AA, shift=4)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)


# ----------------------------------------------------------------- image
GRAIN_RES = (1372, 772)


def render_frame(t, W, H):
    init_data()
    global LUT, TREV, SNAP_T
    if LUT is None:
        LUT = build_lut()
    if TREV is None:
        TREV = build_trev()
    if SNAP_T is None:
        SNAP_T = find_snap_time()
    S = H / 1080.0
    C, Z, rot = camera(t)
    # micro-secousse de caméra sur l'impact de la séparation (~2 px en 1080p)
    tau = t - SNAP_T
    if 0 <= tau < 0.6:
        amp = 2.2 * math.exp(-tau / 0.11) / Z
        C = C + amp * np.array([math.sin(2 * math.pi * 17 * tau + 0.3), math.sin(2 * math.pi * 13 * tau + 1.9)])
    Zs = Z * S
    A_logo = affine_screen_to_logo(C, Z, rot, W, H, S)
    st = shape_state(t)

    # --- intensité globale de la lumière
    hb = heartbeat(t)
    ign = ease_io_sine(seg(t, *T_IGNITE))
    gain = ign * (1 + 0.20 * hb) + 0.10 * hb * (1 - ign)
    tension = smooth(seg(t, SNAP_T - 0.45, SNAP_T))
    flash = math.exp(-(t - SNAP_T) / 0.16) if t >= SNAP_T else 0.0
    gain *= 1 + 0.08 * tension + 0.24 * flash
    out_k = ease_in3(seg(t, *FADE))
    gain *= 1 - out_k
    # respiration lente de la lumière une fois le logo posé
    gain *= 1 + smooth(seg(t, 6.3, 7.0)) * (0.018 * math.sin(2 * math.pi * 0.55 * (t - 6.3))
                                            + 0.006 * math.sin(2 * math.pi * 2.3 * t + 1.0))

    # --- symbole
    dS = symbol_sdf(t, st, A_logo, W, H)
    E_sym, _ = shape_emission(dS, Zs)
    E_sym *= gain
    R_sym = lerp(70.0, 24.0, ease_out3(seg(t, 0.15, 1.7)))
    R_sym = lerp(R_sym, 20.0, seg(t, 1.7, RACK[0]))
    R_sym *= 1 - ease_io3(seg(t, *RACK))
    R_sym += 9.0 * ease_in3(seg(t, *FADE))
    E = defocus(E_sym, R_sym * S)

    # --- phrase manuscrite (plan de netteté différent)
    txt = text_layer(t, W, H, S)
    if txt is not None:
        E_txt, x0, y0 = txt
        E[y0:y0 + E_txt.shape[0], x0:x0 + E_txt.shape[1]] += E_txt

    # --- wordmark
    E_w = word_layer(t, A_logo, W, H, Zs)
    if E_w is not None:
        wg = (1 - ease_in3(seg(t, FADE[0] - 0.1, FADE[1] - 0.05)))
        R_w = 5.0 * S * (1 - ease_out3(seg(t, WORD, WORD + 0.7)))
        E += defocus(E_w * wg, R_w)

    # --- poussières
    light_xy = ((GEO["orb_c"] - C) * Z)
    light_xy = (light_xy[0] + 960, light_xy[1] + 540)
    dust_gain = ign * (1 - smooth(clamp01(pchip(t, CAM_KEYS) / 0.8)))
    if dust_gain > 0.002:
        E += dust_layer(t, C, Z, W, H, S, light_xy, dust_gain)

    # --- bloom / halation / traînée anamorphique
    small = cv2.resize(E, (480, 270), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 3.0)
    b2 = cv2.GaussianBlur(small, (0, 0), 10.0)
    b3 = cv2.GaussianBlur(cv2.resize(small, (240, 135), interpolation=cv2.INTER_AREA), (0, 0), 15.0)
    b3 = cv2.resize(b3, (480, 270), interpolation=cv2.INTER_LINEAR)
    bloom = (0.10 * b1 + 0.07 * b2 + 0.06 * b3) * (1 + 1.5 * flash)
    bloom = cv2.resize(bloom, (W, H), interpolation=cv2.INTER_LINEAR)
    # le profil du logo est calibré sur la photo : le bloom n'éclaire que l'obscurité
    keep = np.clip((1.0 - E) / 0.7, 0.0, 1.0)
    E = E + bloom * keep * keep

    rgb = tonemap(E)

    # --- fond, aberration chromatique, vignettage
    bg = np.array([0.026, 0.020, 0.024], np.float32)
    rgb = rgb + bg * (1 - rgb)
    ca = 0.0011
    for ch, s in ((0, 1 + ca), (2, 1 - ca)):
        M = np.array([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]], np.float64)
        rgb[:, :, ch] = cv2.warpAffine(np.ascontiguousarray(rgb[:, :, ch]), M, (W, H), flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_REPLICATE)
    yy, xx = np.ogrid[0:H, 0:W]
    rr = ((xx - W / 2) / (W / 2)) ** 2 * 0.7 + ((yy - H / 2) / (H / 2)) ** 2 * 0.55
    vig = (1 - 0.32 * np.clip(rr, 0, 1.6) ** 1.3).astype(np.float32)
    rgb *= vig[:, :, None]

    # --- grain argentique (taille relative à l'image, identique en 1080p et 4K)
    rng = np.random.default_rng(1000 + int(round(t * 1000)))
    gw, gh = GRAIN_RES
    gl = rng.standard_normal((gh, gw), np.float32)
    gc = rng.standard_normal((gh, gw), np.float32)
    gl = cv2.resize(gl, (W, H), interpolation=cv2.INTER_CUBIC)
    gc = cv2.resize(gc, (W, H), interpolation=cv2.INTER_CUBIC)
    lum = rgb[:, :, 0] * 0.3 + rgb[:, :, 1] * 0.59 + rgb[:, :, 2] * 0.11
    grain_amt = 1.0 - 0.5 * seg(t, FADE[1], DURATION)
    amp = (0.011 + 0.045 * lum * (1.15 - lum)) * grain_amt
    rgb += (gl * amp)[:, :, None]
    dark = np.clip(1 - lum * 3, 0, 1) * grain_amt
    rgb += (gc * dark * 0.009)[:, :, None] * np.array([1.0, 0.25, 0.2], np.float32)
    return np.clip(rgb, 0, 1)


def to_bgr8(rgb):
    return (rgb[:, :, ::-1] * 255.0 + 0.5).astype(np.uint8)


# ----------------------------------------------------------------- CLI
def _job(args):
    i, W, H, outdir, fps = args
    t = i / fps
    img = render_frame(t, W, H)
    cv2.imwrite(os.path.join(outdir, f"{i:04d}.png"), to_bgr8(img), [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=1080, help="hauteur de sortie (540, 1080, 2160)")
    ap.add_argument("--times", type=str, default="", help="instants à prévisualiser, ex: 1,4.5")
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--fps", type=float, default=FPS, help="images par seconde (24, 25, 30, 60...)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=-1)
    a = ap.parse_args()
    H = a.res
    W = H * 16 // 9
    init_data()
    if a.times:
        global SNAP_T
        SNAP_T = find_snap_time()
        print(f"rupture du pont : t = {SNAP_T:.3f} s")
        ts = [float(x) for x in a.times.split(",")]
        out = a.out or os.path.join(assets.ROOT, "output", "preview")
        os.makedirs(out, exist_ok=True)
        tiles = []
        for t in ts:
            img = to_bgr8(render_frame(t, W, H))
            cv2.putText(img, f"{t:.2f}s", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(out, f"t{t:05.2f}.png"), img)
            tiles.append(img)
        cols = 3
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        cv2.imwrite(os.path.join(out, "contact.png"), np.vstack(rows))
        return
    n = int(round(DURATION * a.fps))
    end = n if a.end < 0 else a.end
    out = a.out or os.path.join(assets.ROOT, "output", f"frames_{H}")
    os.makedirs(out, exist_ok=True)
    jobs = [(i, W, H, out, a.fps) for i in range(a.start, end)]
    with Pool(a.jobs, initializer=init_data) as pool:
        for k, i in enumerate(pool.imap_unordered(_job, jobs)):
            if k % 24 == 0:
                print(f"{k}/{len(jobs)}", flush=True)
    print("ok", out)


if __name__ == "__main__":
    main()
