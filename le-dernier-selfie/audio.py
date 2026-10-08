"""Bande-son de LE DERNIER SELFIE, synthétisée et calée sur la chorégraphie de render.py.

L'idée : chaque personne est une note. Quand la lampe s'allume, les dix notes forment un accord
(ré mineur étalé sur quatre octaves). À chaque départ, la note de celui qui s'en va s'éteint, et une
note de boîte à musique tinte au moment où son regard reste suspendu. L'accord se vide avec la
pièce ; il ne reste que le souffle de la salle, la lampe qui grésille, puis le silence.

Sons : yeux qui s'allument (tintements de verre), interrupteur + bourdonnement de l'ampoule,
froissements de vêtements quand on se lève, pas feutrés spatialisés (gauche / droite selon la
sortie), secousse du téléphone, grésillement et extinction, souffle grave quand les yeux du couloir
s'ouvrent, coupure sèche.

  python3 audio.py        -> output/le_dernier_selfie_audio.wav (48 kHz)
"""
import json
import math
import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from render import CAST, DURATION, FPS, SHAKE_AT, STEP, TIMELINE, exposure, gaze_release

SR = 48000
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
rng = np.random.default_rng(12)
N = int(DURATION * SR)
L = np.zeros(N, np.float32)
R = np.zeros(N, np.float32)
T = TIMELINE
W_IMG = 1844.0

# une note par personne, dans l'ordre des départs : le premier qui part emporte la plus aiguë
CHORD = [587.33, 440.00, 349.23, 329.63, 261.63, 220.00, 174.61, 146.83, 110.00, 73.42]
# la boîte à musique : une phrase qui descend, un tintement par regard
MUSIC_BOX = [880.00, 698.46, 659.26, 587.33, 523.25, 440.00, 349.23, 329.63, 293.66, 220.00]


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def add(sig, t0, pan=0.0, gain=1.0):
    """Place un son à t0 (s), panoramique -1 (gauche) .. 1 (droite), loi à puissance constante."""
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0] * gain
    a = (pan + 1) * math.pi / 4
    L[i0:i0 + len(sig)] += sig * math.cos(a)
    R[i0:i0 + len(sig)] += sig * math.sin(a)


def tvec(d):
    return np.arange(int(d * SR)) / SR


def pan_of(x):
    return float(np.clip((x / W_IMG) * 2 - 1, -0.9, 0.9))


def glint(f, d=1.2):
    t = tvec(d)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.01 * t)
    return (s * np.exp(-t / 0.35) * np.minimum(t / 0.004, 1)).astype(np.float32)


def music_box(f, d=3.0):
    t = tvec(d)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1)
         + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.35)
         + 0.20 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t / 0.12))
    click = highpass(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.002) * 0.15
    return ((s + click) * np.minimum(t / 0.003, 1)).astype(np.float32)


def thump(d=0.35, f=62, soft=1.0):
    t = tvec(d)
    body = np.sin(2 * np.pi * f * t * (1 - 0.25 * t / d)) * np.exp(-t / 0.07)
    tap = lowpass(rng.standard_normal(len(t)), 420) * np.exp(-t / 0.03) * 0.8 * soft
    return (body + tap).astype(np.float32)


def rustle(d):
    t = tvec(d)
    n = bandpass(rng.standard_normal(len(t)), 900, 4200)
    crinkle = np.clip(lowpass(rng.standard_normal(len(t)), 18) * 4, 0, None)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7
    return (n * crinkle * env).astype(np.float32)


def click(d=0.06, f=1300):
    t = tvec(d)
    n = highpass(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.0025)
    ping = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012) * 0.3
    return (n + ping).astype(np.float32)


# ------------------------------------------------------------------ ambiance

t_all = np.arange(N) / SR
# souffle de la salle (bruit brun filtré), présent dès le noir, un peu plus dense quand la lampe brûle
brown = np.cumsum(rng.standard_normal(N)).astype(np.float32)
brown = highpass(brown, 25)
brown = lowpass(brown, 380) / (np.abs(brown).max() + 1e-9)
room = brown * 0.05
room[t_all >= T["cut"]] = 0
add(room, 0, -0.2)
add(np.roll(room, 9000), 0, 0.2)

# exposition de la lampe échantillonnée (12 poses/s) -> bourdonnement de l'ampoule
pose_t = (np.floor(t_all * FPS / STEP) * STEP / FPS)
uniq, inv = np.unique(pose_t, return_inverse=True)
ex = np.array([exposure(u) for u in uniq], np.float32)[inv]
ex_s = lowpass(ex, 60)
hum = (np.sin(2 * np.pi * 100 * t_all) + 0.5 * np.sin(2 * np.pi * 200 * t_all) + 0.25 * np.sin(2 * np.pi * 300 * t_all))
hum = (hum * ex_s * 0.018).astype(np.float32)
add(hum, 0, -0.55)

# ------------------------------------------------------------------ ouverture : les yeux

for k in range(10):
    add(glint(1568 * 2 ** (k / 24)), T["eyes_on"] + 0.11 * k, pan=-0.7 + 0.15 * k, gain=0.05)
add(click(), T["lamp_on"] - 0.03, pan=-0.6, gain=0.10)
# démarrage de l'ampoule : petits claquements à chaque saut de lumière
for k in range(5):
    add(click(0.03, 2400), T["lamp_on"] + k / 12, pan=-0.6, gain=0.12)

# ------------------------------------------------------------------ l'accord qui se vide

for idx, c in enumerate(CAST):
    f = CHORD[idx]
    t_end = c["start"] + c["ant"] + 0.2
    d = t_end + 3.0 - T["lamp_on"]
    t = tvec(d)
    voice = sum(np.sin(2 * np.pi * f * (1 + det) * t + ph)
                for det, ph in ((-0.0016, 0.0), (0.0, 1.3), (0.0019, 2.1)))
    voice += 0.18 * np.sin(2 * np.pi * 2 * f * t + 0.7)
    trem = 1 + 0.12 * np.sin(2 * np.pi * (0.13 + 0.03 * idx) * t + idx)
    fade_in = np.clip(t / 3.0, 0, 1) ** 2
    fade_out = np.clip(1 - (t - (t_end - T["lamp_on"])) / 2.6, 0, 1) ** 1.5
    amp = 0.022 * (220 / f) ** 0.35
    sig = (voice * trem * fade_in * fade_out * amp).astype(np.float32)
    sig = lowpass(sig, 2500).astype(np.float32)
    add(sig, T["lamp_on"], pan=0.35 * math.sin(idx * 1.9))

# ------------------------------------------------------------------ les départs

meta = json.load(open(os.path.join(ROOT, "assets", "layers", "puppets.json")))
for idx, c in enumerate(CAST):
    info = meta["people"][str(c["p"])]
    x = info["center"][0]
    st, ant = c["start"], c["ant"]
    rd, _ = c["rise"]
    wd, wdx, _ = c["walk"]
    # froissement en se levant
    add(rustle(ant + max(rd, 0.6)), st + 0.1, pan_of(x), gain=0.05)
    # le regard qui reste : la boîte à musique tinte quand il se détache
    add(music_box(MUSIC_BOX[idx]), gaze_release(c), pan_of(x) * 0.6, gain=0.11)
    # les pas, de plus en plus loin
    t2 = st + ant + rd
    steps = c["steps"]
    for k in range(1, steps + 1):
        w = k / steps
        e = (w ** 3) * 0.65 + (w * w * (3 - 2 * w)) * 0.35
        xs = x + wdx * e
        g = 0.5 * (1 - 0.55 * w)
        add(thump(f=58 + 6 * rng.random(), soft=0.9), t2 + w * wd - 0.02, pan_of(xs), gain=g * 0.5)

# le téléphone quitte la main
add(thump(0.6, 48), SHAKE_AT, -0.4, 0.30)
for k in range(3):
    add(bandpass(rng.standard_normal(int(0.05 * SR)), 1500, 6000).astype(np.float32)
        * np.exp(-tvec(0.05) / 0.01).astype(np.float32), SHAKE_AT + 0.04 + 0.07 * k, -0.4, 0.12)

# ------------------------------------------------------------------ la lampe vacille, s'éteint

k0 = int(T["lamp_flicker"] * FPS / STEP)
k1 = int(T["lamp_off"] * FPS / STEP)
prev = exposure(k0 * STEP / FPS)
for k in range(k0, k1 + 1):
    tk = k * STEP / FPS
    e = exposure(tk)
    if abs(e - prev) > 0.25:
        burst = highpass(rng.standard_normal(int(0.07 * SR)), 1200) * np.exp(-tvec(0.07) / 0.012)
        add(burst.astype(np.float32), tk, -0.55, 0.10 * abs(e - prev))
    prev = e
add(click(0.08, 900), T["lamp_off"], -0.55, 0.12)

# ------------------------------------------------------------------ au fond du couloir

d = T["cut"] - T["last_eyes"]
t = tvec(d)
swell = np.clip(t / 0.9, 0, 1) ** 2
breath = lowpass(rng.standard_normal(len(t)), 220) * 3.0 * swell
sub = np.sin(2 * np.pi * 41.2 * t) * swell
glass = np.sin(2 * np.pi * 1760 * t) * np.clip((t - 0.2) / 0.8, 0, 1) * 0.15
add((0.05 * breath + 0.12 * sub + 0.03 * glass).astype(np.float32), T["last_eyes"], 0.0)
add(click(0.03, 3000), T["last_blink"], 0.0, 0.12)

# ------------------------------------------------------------------ coupure sèche et mixage

cut = int(T["cut"] * SR)
L[cut:] = 0
R[cut:] = 0
st = np.stack([L, R], axis=1)
fade = np.ones(N, np.float32)
fade[:int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
fade[cut - int(0.004 * SR):cut] = np.linspace(1, 0, int(0.004 * SR))
st *= fade[:, None]


def loudness(x):
    """Sonie intégrée (LUFS) mesurée par ffmpeg (EBU R128)."""
    p = os.path.join(OUT, "_measure.wav")
    wavfile.write(p, SR, x.astype(np.float32))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    os.remove(p)
    return float(r.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0])


def limiter(x, ceil_db=-1.5, release=0.12, block=48):
    """Limiteur à anticipation : gain calculé par blocs d'1 ms, attaque immédiate, relâchement doux."""
    ceil = 10 ** (ceil_db / 20)
    nb = len(x) // block + 1
    pad = np.zeros((nb * block, 2), np.float32)
    pad[:len(x)] = x
    pk = np.abs(pad).reshape(nb, block, 2).max(axis=(1, 2))
    pk = np.maximum.reduce([np.roll(pk, k) for k in (-2, -1, 0, 1)])
    want = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    g = np.empty(nb)
    cur, k_rel = 1.0, math.exp(-block / (release * SR))
    for i in range(nb):
        cur = want[i] if want[i] < cur else want[i] + (cur - want[i]) * k_rel
        g[i] = cur
    gs = np.interp(np.arange(len(x)), np.arange(nb) * block + block / 2, g)
    return x * gs[:, None].astype(np.float32)


os.makedirs(OUT, exist_ok=True)
TARGET = -18.0      # sonie de film, la dynamique est gardée (YouTube normalise à -14)
st = st / (np.abs(st).max() + 1e-9) * 0.5
for _ in range(2):
    st = limiter(st * 10 ** ((TARGET - loudness(st)) / 20))
print(f"sonie {loudness(st):.1f} LUFS, crête {20 * np.log10(np.abs(st).max()):.1f} dBFS")
tmp = os.path.join(OUT, "_audio_f32.wav")
wavfile.write(tmp, SR, st.astype(np.float32))
dst = os.path.join(OUT, "le_dernier_selfie_audio.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "pcm_s24le", dst], check=True)
os.remove(tmp)
print("ok", dst)
