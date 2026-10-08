"""LE DERNIER SELFIE — rendu image par image.

Style : stop-motion réaliste. Les poses changent 12 fois par seconde (animation « en deux » sur
une base 24 i/s), chaque marionnette tremble imperceptiblement d'une pose à l'autre comme si une main
l'avait replacée, la lumière varie d'un cliché à l'autre. Les personnages tournent en 3D grâce
à la carte de profondeur (relief déplacé), la caméra pousse lentement.

Récit (les temps sont dans TIMELINE / CAST ci-dessous) :
  noir → vingt yeux s'allument dans l'obscurité → la lampe s'allume : le groupe, figé pour le selfie
  → un à un, ils se lèvent et sortent du cadre ; leur regard reste un instant après eux
  → celui qui tient le téléphone reste seul, puis part à son tour (le cadre tressaille)
  → le canapé vide → la lampe vacille et s'éteint → au fond du couloir, deux yeux s'ouvrent.

  python3 render.py                       # film complet -> output/le_dernier_selfie_1080p.mp4 (sans son)
  python3 render.py --still 3.0,12.5,29   # images fixes -> output/preview/
"""
import argparse
import json
import math
import os
import subprocess
import zlib

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
LAY = os.path.join(ROOT, "assets", "layers")
OUT = os.path.join(ROOT, "output")

FPS = 24
STEP = 2                      # une pose toutes les 2 images = 12 poses/s
DURATION = 35.0
OUT_W, OUT_H = 1920, 1080
CONTENT_H = 888               # 1920/1844*853 ≈ 888 : format 2,16:1, bandes noires de 96 px

# --- temps forts ---
TIMELINE = {
    "eyes_on": 0.6,           # les yeux apparaissent dans le noir
    "lamp_on": 2.3,           # la lampe s'allume
    "lamp_flicker": 30.4,     # la lampe vacille
    "lamp_off": 31.5,         # et s'éteint
    "last_eyes": 32.6,        # deux yeux au fond du couloir
    "last_blink": 33.7,
    "cut": 34.4,              # noir final
}
DOORWAY_EYES = (936.0, 236.0, 15.0)   # x, y, écart entre les yeux (personnage lointain dans le couloir)

# --- distribution : qui part, quand, comment ---
#   start : début du départ (s)   ant : anticipation (s)   rise : se lever (durée s, hauteur px)
#   walk  : sortir (durée s, dx, dy)   yaw : rotation 3D en se levant puis en sortant (degrés)
#   steps : pas pendant la sortie     scale : grossit en se levant (rapproché de l'objectif)
CAST = [
    dict(p=9, start=4.6, ant=0.35, rise=(1.2, 200), walk=(1.9, 900, -60), yaw=(10, 30), steps=4, scale=1.00),
    dict(p=7, start=6.5, ant=0.35, rise=(1.2, 190), walk=(1.9, -850, -60), yaw=(-10, -30), steps=4, scale=1.00),
    dict(p=5, start=8.3, ant=0.40, rise=(1.0, 130), walk=(1.8, 820, -30), yaw=(14, 30), steps=4, scale=1.02),
    dict(p=8, start=10.0, ant=0.40, rise=(1.0, 120), walk=(1.8, -800, -30), yaw=(-14, -30), steps=4, scale=1.02),
    dict(p=4, start=11.6, ant=0.35, rise=(1.2, 200), walk=(1.9, 1000, -50), yaw=(10, 28), steps=4, scale=1.00),
    dict(p=3, start=13.3, ant=0.40, rise=(0.9, 100), walk=(1.7, 700, -20), yaw=(18, 32), steps=4, scale=1.03),
    dict(p=0, start=15.2, ant=0.60, rise=(2.0, 300), walk=(2.2, -1100, -40), yaw=(-6, -26), steps=5, scale=1.02),
    dict(p=2, start=17.8, ant=0.45, rise=(1.4, 260), walk=(1.9, 800, -40), yaw=(14, 30), steps=4, scale=1.05),
    dict(p=6, start=20.6, ant=0.60, rise=(1.8, 300), walk=(2.0, 1000, -40), yaw=(10, 28), steps=4, scale=1.03),
    dict(p=1, start=23.9, ant=0.90, rise=(0.0, 0), walk=(2.6, -720, 300), yaw=(-6, -24), steps=3, scale=1.00),
]
SHAKE_AT = 24.9               # le téléphone quitte la main : le cadre tressaille

Z_PX = 1100.0                 # relief : pixels de déplacement par unité de profondeur relative


# ---------------------------------------------------------------- utilitaires

def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ease_in(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def hrand(*key):
    """Bruit déterministe dans [-1, 1] pour une clé (personne, pose...)."""
    h = zlib.crc32(repr(key).encode())
    return np.random.default_rng(h).uniform(-1, 1)


def smooth_noise(t, seed, freq=0.25):
    """Dérive lente et douce (somme de sinus)."""
    return (math.sin(t * freq * 6.283 + seed * 1.7) * 0.6 + math.sin(t * freq * 2.71 * 6.283 + seed * 3.1) * 0.4)


# ---------------------------------------------------------------- données

class Puppet:
    def __init__(self, i, meta):
        self.i = i
        info = meta["people"][str(i)]
        rgba = cv2.imread(os.path.join(LAY, f"p{i}.png"), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        a = rgba[..., 3:4]
        self.pm = np.concatenate([rgba[..., :3] * a, a], axis=2)      # prémultiplié
        z = cv2.imread(os.path.join(LAY, f"p{i}_z.png"), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
        self.z = (z - info["depth"]) * Z_PX
        self.x0, self.y0 = info["bbox"][0], info["bbox"][1]
        self.cx, self.cy = info["center"]
        self.top = info["top"]
        self.eyes = info["eyes"]
        self.rank = info["rank"]

    def warp_yaw(self, yaw_deg):
        """Rotation autour d'un axe vertical passant par le centre, avec le relief de la profondeur."""
        if abs(yaw_deg) < 0.05:
            return self.pm, 0
        pad = 90
        pm = cv2.copyMakeBorder(self.pm, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=0)
        z = cv2.copyMakeBorder(self.z, 0, 0, pad, pad, cv2.BORDER_REPLICATE)
        h, w = z.shape
        th = math.radians(yaw_deg)
        c, s = math.cos(th), math.sin(th)
        px = self.cx - self.x0 + pad
        xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        sx = px + (xs - px) / c
        for _ in range(3):
            zz = cv2.remap(z, sx, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            sx = px + (xs - px - zz * s) / c
        out = cv2.remap(pm, sx, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        # la face qui se détourne de la lampe s'assombrit un peu
        out[..., :3] *= 1 - 0.18 * abs(s)
        return out, pad


def load():
    meta = json.load(open(os.path.join(LAY, "puppets.json")))
    plate = cv2.imread(os.path.join(LAY, "plate.png")).astype(np.float32) / 255
    src = cv2.imread(os.path.join(ROOT, "assets", "source", "selfie.png")).astype(np.float32) / 255
    puppets = {i: Puppet(i, meta) for i in range(len(meta["people"]))}
    return meta, plate, src, puppets


# ---------------------------------------------------------------- chorégraphie

def pose_of(c, t):
    """Paramètres de la marionnette au temps t : dx, dy, rot, sc, sy, yaw, visible."""
    st, ant = c["start"], c["ant"]
    rd, rh = c["rise"]
    wd, wdx, wdy = c["walk"]
    y1, y2 = c["yaw"]
    side = 1 if wdx >= 0 else -1
    seed = c["p"]
    # vie au repos : respiration + micro-mouvements de tête
    breath = math.sin(t * 6.283 / (3.2 + 0.3 * seed) + seed)
    dx = 1.2 * smooth_noise(t, seed, 0.11)
    dy = 1.0 * smooth_noise(t, seed + 9, 0.13)
    rot = 0.35 * smooth_noise(t, seed + 3, 0.09)
    sc = 1.0
    sy = 1 + 0.0035 * breath
    yaw = 0.0
    if t < st:
        return dict(dx=dx, dy=dy, rot=rot, sc=sc, sy=sy, yaw=yaw, vis=True)
    # 1) anticipation : on se tasse un peu, on penche vers la sortie
    u = ease((t - st) / ant)
    dy += 9 * math.sin(math.pi * min(u, 1.0))
    sy -= 0.012 * math.sin(math.pi * min(u, 1.0))
    rot += -side * 1.4 * u
    yaw += y1 * 0.25 * u
    t1 = st + ant
    if t >= t1 and rd > 0:
        # 2) se lever : départ lent, arrivée amortie
        v = (t - t1) / rd
        e = ease(v)
        dy -= rh * e
        sc *= 1 + (c["scale"] - 1) * e
        rot += side * 1.4 * e
        yaw += (y1 - y1 * 0.25) * e
        dx += side * 18 * e
    t2 = t1 + rd
    if t >= t2:
        # 3) sortir du cadre en marchant : accélère, petits rebonds de pas
        w = (t - t2) / wd
        e = ease_in(w) * 0.65 + ease(w) * 0.35
        dx += wdx * e
        dy += wdy * e
        yaw += (y2 - y1) * ease(w)
        steps = c["steps"]
        dy -= 10 * abs(math.sin(math.pi * steps * min(w, 1.0)))
        rot += side * 1.5 * math.sin(math.pi * steps * min(w, 1.0))
    vis = t < t2 + wd + 0.1
    return dict(dx=dx, dy=dy, rot=rot, sc=sc, sy=sy, yaw=yaw, vis=vis)


def jitter(i, k):
    """Le tremblement de la stop-motion : chaque pose est replacée à la main."""
    return dict(dx=0.55 * hrand(i, k, 1), dy=0.55 * hrand(i, k, 2), rot=0.10 * hrand(i, k, 3),
                gain=1 + 0.012 * hrand(i, k, 4))


def exposure(t):
    """Lumière de la pièce : noir, la lampe s'allume (démarrage hésitant), vacille et s'éteint."""
    T = TIMELINE
    if t < T["lamp_on"]:
        return 0.0
    k = int((t - T["lamp_on"]) * 12)
    seq = [0.55, 0.12, 0.85, 0.35, 1.0]
    if k < len(seq):
        return seq[k]
    if T["lamp_flicker"] <= t < T["lamp_off"]:
        kk = int((t - T["lamp_flicker"]) * 12)
        pat = [1, 0.62, 1, 1, 0.4, 0.9, 1, 1, 0.3, 0.75, 0.2, 0.55, 0.15, 0.3]
        return pat[kk % len(pat)]
    if t >= T["lamp_off"]:
        return 0.0
    # la pièce se vide, elle se refroidit à peine
    gone = sum(1 for c in CAST if t > c["start"] + c["ant"])
    return 1.0 - 0.012 * gone


def gaze_release(c, dist=70.0):
    """Instant où les yeux de la personne se sont éloignés de `dist` px de leur place : le regard
    s'en détache et reste suspendu là où il était."""
    t = c["start"]
    while t < DURATION:
        q = pose_of(c, t)
        if math.hypot(q["dx"], q["dy"]) > dist:
            return t
        t += 1 / FPS
    return DURATION


def eye_afterglow(t):
    """Intensité des regards qui restent après le départ de chacun."""
    out = []
    for c in CAST:
        t0 = c.setdefault("_gaze", gaze_release(c))
        if t > t0:
            a = math.exp(-(t - t0) / 2.6) * min((t - t0) / 0.35, 1.0)
            out.append((c["p"], a))
    return out


# ---------------------------------------------------------------- rendu

class Renderer:
    def __init__(self):
        self.meta, self.plate, self.src, self.pup = load()
        self.order = sorted(self.pup, key=lambda i: self.pup[i].rank)
        self.H, self.W = self.plate.shape[:2]
        self.cast = {c["p"]: c for c in CAST}
        # masque des yeux dans l'image d'origine (pour l'ouverture dans le noir)
        lum = cv2.cvtColor((self.src * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
        tophat = lum - cv2.morphologyEx(lum, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
        lab = cv2.imread(os.path.join(LAY, "labels.png"), 0)
        eyem = np.clip((tophat - 25) / 40, 0, 1) * (lab > 0)
        self.eye_layer = self.src * eyem[..., None]
        self.grain_rng = np.random.default_rng(1)
        yy, xx = np.mgrid[0:CONTENT_H, 0:OUT_W].astype(np.float32)
        r = np.hypot((xx - OUT_W / 2) / (OUT_W / 2), (yy - CONTENT_H / 2) / (CONTENT_H / 2))
        self.vignette = (1 - 0.38 * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None]

    def puppet_layer(self, i, t, k):
        c = self.cast[i]
        P = self.pup[i]
        q = pose_of(c, t)
        if not q["vis"]:
            return None
        j = jitter(i, k)
        pm, pad = P.warp_yaw(q["yaw"])
        # affine : rotation + échelle autour du centre de la personne, puis translation
        px, py = P.cx, P.cy
        ang = math.radians(q["rot"] + j["rot"])
        ca, sa = math.cos(ang) * q["sc"], math.sin(ang) * q["sc"]
        sy = q["sy"]
        # coordonnées : pixel du calque (u, v) -> image (u + x0 - pad, v + y0)
        A = np.array([[ca, -sa * sy], [sa, ca * sy]], np.float32)
        off = np.array([self.pup[i].x0 - pad - px, self.pup[i].y0 - py], np.float32)
        tr = np.array([px + q["dx"] + j["dx"], py + q["dy"] + j["dy"]], np.float32) + A @ off
        M = np.hstack([A, tr[:, None]])
        lay = cv2.warpAffine(pm, M, (self.W, self.H), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        lay[..., :3] *= j["gain"]
        return lay

    @staticmethod
    def glow_rgb(glow):
        g = cv2.GaussianBlur(glow, (0, 0), 1.6) * 2.2 + cv2.GaussianBlur(glow, (0, 0), 7) * 3.0
        return g[..., None] * np.array([0.86, 0.93, 1.0], np.float32)

    def scene(self, t, k):
        img = self.plate.copy()
        # les regards qui restent sont posés dans le décor, derrière les personnes : on ne les voit
        # que lorsque la place est libre
        glow = np.zeros(self.plate.shape[:2], np.float32)
        for i, a in eye_afterglow(t):
            for (ex_, ey_, _) in self.pup[i].eyes:
                cv2.circle(glow, (int(ex_), int(ey_)), 3, a, -1)
        if glow.max() > 0:
            img = img + self.glow_rgb(glow)
        for i in self.order:
            lay = self.puppet_layer(i, t, k)
            if lay is None:
                continue
            a = lay[..., 3:4]
            img = img * (1 - a) + lay[..., :3]
        return img

    def camera(self, t, k):
        """Échelle et centre (coordonnées source) : poussée lente + flottement + secousse finale."""
        s0 = OUT_W / self.W
        u = ease(t / TIMELINE["lamp_off"])
        s = s0 * (1.035 + 0.065 * u)
        cx = self.W / 2 + 6 * smooth_noise(t, 41, 0.05) + 3 * hrand("cam", k, 1) * 0.25
        cy = self.H / 2 - 10 * u + 4 * smooth_noise(t, 42, 0.05) + 3 * hrand("cam", k, 2) * 0.25
        roll = 0.0
        if t > SHAKE_AT:
            d = t - SHAKE_AT
            amp = math.exp(-d / 0.35) * (d < 2.0)
            cx += 9 * amp * hrand("shake", k, 1)
            cy += 12 * amp * hrand("shake", k, 2) + 6 * amp
            roll = 0.7 * amp * hrand("shake", k, 3)
        return s, cx, cy, roll

    def frame(self, f):
        t_real = f / FPS
        k = f // STEP                      # indice de pose (animation « en deux »)
        t = k * STEP / FPS
        T = TIMELINE
        if t_real >= T["cut"]:
            return np.zeros((OUT_H, OUT_W, 3), np.uint8)

        if t < T["lamp_on"]:
            img = np.zeros_like(self.plate)
        elif t < T["lamp_off"]:
            img = self.scene(t, k) * exposure(t) * (1 + 0.010 * hrand("light", k))
        else:
            img = self.plate * 0.035          # lampe éteinte : on devine à peine la pièce
        # ouverture : les yeux s'allument un à un dans le noir
        if t < T["lamp_on"] + 0.42:
            if t >= T["eyes_on"]:
                lit = np.zeros(self.plate.shape[:2], np.float32)
                for idx, i in enumerate(self.order[::-1]):
                    t_i = T["eyes_on"] + 0.11 * idx
                    if t >= t_i:
                        for (ex_, ey_, _) in self.pup[i].eyes:
                            cv2.circle(lit, (int(ex_), int(ey_)), 16, 1.0, -1)
                lit = cv2.GaussianBlur(lit, (0, 0), 3)[..., None]
                img = np.maximum(img, self.eye_layer * lit * 1.25)
        # les yeux au fond du couloir
        glow = np.zeros(self.plate.shape[:2], np.float32)
        if T["last_eyes"] <= t < T["cut"]:
            u = min((t - T["last_eyes"]) / 0.5, 1.0)
            blink = 0.0 if T["last_blink"] <= t < T["last_blink"] + 2 * STEP / FPS else 1.0
            x, y, d = DOORWAY_EYES
            for sx in (-d / 2, d / 2):
                cv2.circle(glow, (int(x + sx), int(y)), 1, 0.9 * u * blink, -1)
        if glow.max() > 0:
            img = img + self.glow_rgb(glow)

        # bloom sur les hautes lumières (yeux, lampe)
        lum = img.mean(axis=2)
        hi = np.clip((lum - 0.55) / 0.45, 0, 1)[..., None] * img
        img = img + cv2.GaussianBlur(hi, (0, 0), 5) * 0.55 + cv2.GaussianBlur(hi, (0, 0), 22) * 0.45

        # caméra
        s, cx, cy, roll = self.camera(t, k)
        M = cv2.getRotationMatrix2D((cx, cy), roll, s)
        M[0, 2] += OUT_W / 2 - cx
        M[1, 2] += CONTENT_H / 2 - cy
        out = cv2.warpAffine(img, M, (OUT_W, CONTENT_H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        out *= self.vignette
        # grain argentique (change à chaque image, même quand la pose est tenue)
        g = self.grain_rng.standard_normal((CONTENT_H // 2, OUT_W // 2)).astype(np.float32)
        g = cv2.resize(g, (OUT_W, CONTENT_H), interpolation=cv2.INTER_LINEAR)
        out = out + (0.012 + 0.014 * (1 - np.clip(out.mean(2, keepdims=True) * 2.5, 0, 1))) * g[..., None]
        out = np.clip(out, 0, 1)
        full = np.zeros((OUT_H, OUT_W, 3), np.float32)
        y0 = (OUT_H - CONTENT_H) // 2
        full[y0:y0 + CONTENT_H] = out
        return (full * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", default=None, help="temps séparés par des virgules")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=DURATION)
    ap.add_argument("--out", default=os.path.join(OUT, "le_dernier_selfie_1080p_muet.mp4"))
    args = ap.parse_args()
    R = Renderer()
    if args.still:
        d = os.path.join(OUT, "preview")
        os.makedirs(d, exist_ok=True)
        for ts in args.still.split(","):
            f = int(round(float(ts) * FPS))
            cv2.imwrite(os.path.join(d, f"still_{float(ts):05.2f}.jpg"), R.frame(f), [cv2.IMWRITE_JPEG_QUALITY, 92])
        return
    f0, f1 = int(args.start * FPS), int(args.end * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
           "-pix_fmt", "yuv420p", "-tune", "film", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        proc.stdin.write(R.frame(f).tobytes())
        if f % 48 == 0:
            print(f"{f / FPS:5.1f} s", flush=True)
    proc.stdin.close()
    proc.wait()
    print("ok", args.out)


if __name__ == "__main__":
    main()
