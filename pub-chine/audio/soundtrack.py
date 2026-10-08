"""Bande-son de « Creator is the new athlete » — musique + bruitages, synthétisés et calés sur timeline.json.

Morceau à 120 BPM (1 mesure = 2 s = un plan), pentatonique de ré :
guzheng (cordes pincées, synthèse Karplus-Strong) + beat électro + basse + nappes,
avec glissandos de guzheng aux moments clés, gong sur « LA CHINE », compteurs, pièces d'or,
whoosh sur les mouvements de caméra, impacts du titre, déclencheur photo, néon, feux d'artifice, sceau.

Usage : python3 audio/soundtrack.py  ->  output/soundtrack.wav (48 kHz, 24 bits)
"""
from __future__ import annotations

import json
import os
import wave

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
T = json.load(open(os.path.join(ROOT, 'timeline.json')))
SR = 48000
DUR = T['duration']
N = int(DUR * SR)
BEAT = 60 / T['bpm']
BAR = 4 * BEAT
RNG = np.random.default_rng(2026)


# ----------------------------------------------------------------------------- outils
def db(x):
    return 10 ** (x / 20)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def nm(s):
    """'F#4' -> fréquence."""
    name, octv = s[:-1], int(s[-1])
    return midi(12 * (octv + 1) + NOTE[name])


def filt(x, kind, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype=kind, fs=SR, output='sos'), x)


def noise(n):
    return RNG.standard_normal(n)


def adsr(n, a=0.005, d=0.2, s=0.0, r=0.05):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-5), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-5)))
    rel = int(r * SR)
    if rel > 0 and n > rel:
        e[-rel:] *= np.linspace(1, 0, rel)
    return e


class Bus:
    def __init__(self):
        self.x = np.zeros((2, N))

    def add(self, sig, t0, gain=1.0, pan=0.0):
        i0 = int(round(t0 * SR))
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2)
        if i0 < 0:
            sig = sig[:, -i0:]; i0 = 0
        n = min(sig.shape[1], N - i0)
        if n > 0:
            self.x[:, i0:i0 + n] += sig[:, :n] * gain


# ----------------------------------------------------------------------------- instruments
def pluck(f, dur=1.6, bright=0.6, decay=0.996):
    """Corde pincée (Karplus-Strong vectorisé par période) — timbre guzheng."""
    n = int(dur * SR)
    P = max(2, int(round(SR / f)))
    out = np.zeros(n + P)
    burst = noise(P)
    burst = filt(burst, 'lowpass', min(SR * 0.45, 1500 + 9000 * bright))
    out[:P] = burst
    k = P
    while k < n + P:
        prev = out[k - P:k]
        nxt = 0.5 * (prev + np.roll(prev, 1)) * decay
        m = min(P, n + P - k)
        out[k:k + m] = nxt[:m]
        k += P
    y = out[P:P + n]
    y += 0.25 * np.sin(2 * np.pi * f * 2 * np.arange(n) / SR) * np.exp(-np.arange(n) / SR / 0.15) * 0.3
    return y / (np.abs(y).max() + 1e-9) * adsr(n, 0.001, dur * 0.6, 0.0, 0.05)


def kick(level=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.22)
    click = filt(noise(n), 'bandpass', (1500, 6000)) * np.exp(-t / 0.004) * 0.35
    return np.tanh((body + click) * 1.6) * level


def clap():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for d in (0.0, 0.012, 0.024):
        e += np.where(t >= d, np.exp(-(t - d) / 0.012), 0)
    e += np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.12) * 0.6, 0)
    return filt(noise(n), 'bandpass', (900, 4200)) * e


def hat(open_=False):
    n = int((0.35 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    return filt(noise(n), 'highpass', 7000) * np.exp(-t / (0.12 if open_ else 0.018))


def snare():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    nz = filt(noise(n), 'bandpass', (1200, 7000)) * np.exp(-t / 0.09)
    return tone * 0.6 + nz


def crash(dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return filt(noise(n), 'highpass', 3500) * np.exp(-t / 0.9) * (1 - np.exp(-t / 0.002))


def sub_boom(dur=2.0, f0=55, f1=32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.4)
    return np.tanh(1.4 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.7) * (1 - np.exp(-t / 0.004))


def whoosh(dur=0.8, f0=300, f1=4000, peak=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = noise(n)
    out = np.zeros(n)
    bands = np.geomspace(200, 9000, 12)
    centre = np.exp(np.log(f0) + (np.log(f1) - np.log(f0)) * (t / dur))
    for c in bands:
        w = np.exp(-0.5 * ((np.log(c) - np.log(centre)) / 0.5) ** 2)
        out += filt(x, 'bandpass', (c / 1.3, min(c * 1.3, SR / 2 - 100))) * w
    env = np.where(t < peak * dur, (t / (peak * dur)) ** 2, np.exp(-(t - peak * dur) / (0.25 * dur)))
    return out * env


def riser(dur=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = t / dur
    nz = whoosh(dur, 250, 7000, 0.98)
    saw = signal.sawtooth(2 * np.pi * np.cumsum(220 * 2 ** (2 * k ** 1.5)) / SR) * 0.3
    saw = filt(saw, 'lowpass', 3000)
    return (nz + saw * k ** 2) * k ** 1.5


def bell(f, dur=2.5, partials=((1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.4, 0.25, 0.35), (8.9, 0.12, 0.2))):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (dur * d * 0.45)) for r, a, d in partials)
    return y * (1 - np.exp(-t / 0.002))


def gong(f=110, dur=5.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for r, a in ((1, 1.0), (1.41, 0.7), (1.98, 0.6), (2.48, 0.45), (3.1, 0.35), (3.97, 0.25), (5.3, 0.18)):
        fr = f * r * (1 + 0.012 * (1 - np.exp(-t / 0.6)))
        y += a * np.sin(2 * np.pi * np.cumsum(fr) / SR + RNG.uniform(0, 6))
    swell = (1 - np.exp(-t / 0.08)) * np.exp(-t / 2.2)
    y = y * swell + filt(noise(n), 'bandpass', (300, 3000)) * np.exp(-t / 0.05) * 0.4
    return y


def pad(freqs, dur, cutoff=1800, attack=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for det in (-0.006, 0.0, 0.0055):
            y += signal.sawtooth(2 * np.pi * f * (1 + det) * t + RNG.uniform(0, 6))
    y = filt(y / (3 * len(freqs)), 'lowpass', cutoff)
    return y * adsr(n, attack, 9e9, 1.0, min(0.6, dur * 0.4))


def epiano(f, dur=1.8):
    """Piano électrique (synthèse FM) pour la séquence de nuit."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 1.0 * t) * 1.6 * np.exp(-t / 0.35)
    y = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 0.9) + 0.2 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.08)
    return y * (1 - np.exp(-t / 0.003))


def bassnote(f, dur, wob=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = 0.6 * np.sin(2 * np.pi * f * t) + 0.4 * filt(signal.square(2 * np.pi * f * t), 'lowpass', 420)
    return y * adsr(n, 0.004, dur * 0.8, 0.6, 0.03)


def woodblock(f=900):
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.3 * t)) * np.exp(-t / 0.03) + filt(noise(n), 'bandpass', (1500, 5000)) * np.exp(-t / 0.003) * 0.4


def coin():
    f = RNG.uniform(2400, 4200)
    return bell(f, 0.5, ((1, 1.0, 1.0), (2.4, 0.6, 0.6), (3.7, 0.3, 0.4)))


def tick():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return filt(noise(n), 'bandpass', (2500, 6000)) * np.exp(-t / 0.004)


def pop(f=600):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    fr = f * (1 + 1.5 * np.exp(-t / 0.01))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.035)


def shutter():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    c1 = filt(noise(n), 'bandpass', (1800, 8000)) * np.exp(-t / 0.006)
    c2 = np.roll(filt(noise(n), 'bandpass', (1200, 6000)) * np.exp(-t / 0.01), int(0.07 * SR))
    whir = filt(noise(n), 'bandpass', (500, 2000)) * np.exp(-((t - 0.04) / 0.03) ** 2) * 0.3
    return c1 + 0.8 * c2 + whir


def crackle(dur=1.5, density=60):
    n = int(dur * SR)
    y = np.zeros(n)
    for _ in range(int(density * dur)):
        i = RNG.integers(0, n - 400)
        y[i:i + 400] += filt(noise(400), 'highpass', 2500) * np.exp(-np.arange(400) / 60) * RNG.uniform(0.2, 1)
    return y * np.exp(-np.arange(n) / SR / (dur * 0.6))


def reverb_ir(rt=2.4, length=3.0, seed=3):
    r = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = np.zeros((2, n))
    for c in range(2):
        nz = r.standard_normal(n)
        lo = filt(nz, 'lowpass', 2500) * np.exp(-t / (rt / 6.91))
        hi = filt(nz, 'highpass', 2500) * np.exp(-t / (rt / 6.91 * 0.5))
        ir[c] = (lo + 0.5 * hi) * (1 - np.exp(-t / 0.01))
    return ir / np.sqrt((ir ** 2).sum() / 2)


def reverb(x, ir, wet):
    return np.stack([signal.fftconvolve(x[c], ir[c])[:N] for c in range(2)]) * wet


# ----------------------------------------------------------------------------- harmonie (une mesure = un accord)
CH = {
    'D': ['D3', 'F#3', 'A3', 'E4'], 'Bm': ['B2', 'D3', 'F#3', 'A3'], 'G': ['G2', 'B2', 'D3', 'A3'], 'A': ['A2', 'C#3', 'E3', 'B3'],
}
BASS = {'D': 'D2', 'Bm': 'B1', 'G': 'G1', 'A': 'A1'}
PENTA = ['D', 'E', 'F#', 'A', 'B']
# barre n (1..31) -> accord
PROG = {4: 'D', 5: 'Bm', 6: 'G', 7: 'A', 8: 'D', 9: 'Bm', 10: 'G', 11: 'A', 12: 'A', 13: 'D', 14: 'Bm',
        15: 'G', 16: 'A', 17: 'D', 18: 'Bm', 19: 'G', 20: 'A', 21: 'D', 22: 'D', 23: 'G',
        24: 'Bm', 25: 'G', 26: 'D', 27: 'A', 28: 'Bm', 29: 'A', 30: 'D', 31: 'D'}


def bar_t(b):
    return (b - 1) * BAR


def penta_run(start_oct=4, count=12, up=True):
    notes = [f'{n}{start_oct + i // 5}' for i, n in enumerate(PENTA * 4)][:count]
    return notes if up else notes[::-1]


# motif guzheng (croches) — 2 mesures
MOTIF = [('D5', 0), ('E5', 0.5), ('F#5', 1), ('A5', 1.5), ('F#5', 2.5), ('E5', 3), ('D5', 3.5),
         ('B4', 4), ('D5', 4.5), ('E5', 5.5), ('A4', 6), ('B4', 6.5), ('D5', 7)]


BUSES = {}


def build():
    drums, bass, music, sfx, keys = Bus(), Bus(), Bus(), Bus(), Bus()
    H, C_, B_, M_, F_ = T['hook'], T['city'], T['brand'], T['modules'], T['founders']
    kicks = []

    # ------------------------------------------------------------ INTRO (0-6 s)
    music.add(pad([nm('D2'), nm('A2')], 6.2, 500, 1.2), 0.0, db(-16))
    fall = np.sin(2 * np.pi * np.cumsum(np.linspace(1800, 300, int(0.65 * SR))) / SR) * np.linspace(0, 1, int(0.65 * SR)) ** 2
    sfx.add(fall, H['cubeDrop'], db(-30))
    sfx.add(sub_boom(2.0), H['cubeLand'], db(-6))
    sfx.add(crash(2.0), H['cubeLand'], db(-20))
    for i, n_ in enumerate(penta_run(3, 15)):
        music.add(pluck(nm(n_), 1.4, 0.5 + i * 0.03), H['ripple'][0] + 0.05 + i * 0.1, db(-13 + i * 0.25), pan=-0.5 + i * 0.07)
    music.add(whoosh(2.6, 200, 5000, 0.95), 3.0, db(-24))
    music.add(pad([nm(x) for x in CH['D']], 3.2, 900, 2.0), 3.0, db(-21))
    sfx.add(whoosh(0.9, 400, 3000, 0.5), H['cubeSink'][0], db(-26))

    # ------------------------------------------------------------ VILLE (6-12 s)
    for i, n_ in enumerate(penta_run(4, 11)):
        music.add(pluck(nm(n_), 1.2, 0.7), 5.55 + i * 0.045, db(-13), pan=-0.6 + i * 0.12)
    sfx.add(gong(98, 5.0), C_['title'][0] - 0.05, db(-17))
    for b in range(4, 7):
        t0 = bar_t(b)
        for beat in (0, 2):
            drums.add(kick(0.9), t0 + beat * BEAT, db(-9)); kicks.append(t0 + beat * BEAT)
        if b >= 5:
            for e in range(8):
                drums.add(hat(), t0 + e * BEAT / 2, db(-29 + (3 if e % 2 else 0)), pan=0.25)
    sfx.add(whoosh(1.2, 300, 2500, 0.4), C_['train'] - 0.1, db(-28), pan=0.5)
    for k in range(14):
        sfx.add(pop(500 + 60 * (k % 7)), 6.0 + k * 0.17 + RNG.uniform(0, 0.05), db(-31), pan=RNG.uniform(-0.6, 0.6))

    # ------------------------------------------------------------ CHIFFRES (12-20 s) + ELDORADO (20-22 s)
    for b in range(7, 12):
        t0 = bar_t(b)
        for beat in range(4):
            drums.add(kick(1.0), t0 + beat * BEAT, db(-8)); kicks.append(t0 + beat * BEAT)
        for beat in (1, 3):
            drums.add(clap(), t0 + beat * BEAT, db(-15))
        for e in range(8):
            drums.add(hat(e % 2 == 1 and e in (3, 7)), t0 + e * BEAT / 2, db(-25 if e % 2 else -29), pan=0.3)
    for i, a in enumerate(T['stats']['cards']):
        for k in range(16):
            sfx.add(tick(), a + 0.1 + k * 0.0625, db(-27 + k * 0.3), pan=0.4 if i else -0.4)
        sfx.add(bell(nm(['A5', 'B5', 'D6', 'E6'][i]), 1.5), a + 1.1, db(-22), pan=0.4 if i else -0.4)
        sfx.add(whoosh(0.45, 800, 4000, 0.6), a - 0.05, db(-30))
    e0 = T['eldorado']['start']
    for k in range(90):
        sfx.add(coin(), e0 + RNG.uniform(0, 2.3), db(-30), pan=RNG.uniform(-0.8, 0.8))
    music.add(pad([nm('A3'), nm('C#4'), nm('E4'), nm('B4')], 2.4, 3000, 0.3), 20.0, db(-19))
    for i, n_ in enumerate(penta_run(5, 10)):
        music.add(pluck(nm(n_), 1.0, 0.8), 20.05 + i * 0.05, db(-14), pan=0.6 - i * 0.12)

    # ------------------------------------------------------------ MARQUE (22-28 s)
    sfx.add(whoosh(1.1, 250, 6000, 0.55), B_['whip'][0], db(-14))
    music.add(riser(1.95), B_['pre'][0] + 0.05, db(-14))
    for k in range(16):
        tt = 23.0 + 1.0 * (1 - (1 - k / 16) ** 1.6)
        drums.add(snare(), tt, db(-24 + k * 0.7))
    slam = B_['slam']
    for i, dt in enumerate((0.0, 0.42, 0.7)):
        sfx.add(sub_boom(2.2, 60, 30), slam + dt, db(-4 if i == 0 else -9))
        sfx.add(filt(noise(int(0.4 * SR)), 'lowpass', 1200) * np.exp(-np.arange(int(0.4 * SR)) / SR / 0.06), slam + dt, db(-12))
    sfx.add(crash(3.0), slam, db(-12))
    crowd_n = int(3.6 * SR)
    ct = np.arange(crowd_n) / SR
    crowd = filt(noise(crowd_n), 'bandpass', (350, 3500)) * (1 - np.exp(-ct / 0.3)) * np.exp(-ct / 1.6)
    crowd *= 1 + 0.3 * np.sin(2 * np.pi * 5.5 * ct + 3 * np.sin(2 * np.pi * 0.7 * ct))
    sfx.add(crowd, slam + 0.05, db(-22))
    for i, n_ in enumerate(penta_run(5, 12, up=False)):
        music.add(pluck(nm(n_), 1.4, 0.8), slam + 0.02 + i * 0.04, db(-12), pan=0.7 - i * 0.12)
    for b in range(13, 15):
        t0 = bar_t(b)
        for beat in range(4):
            drums.add(kick(1.1), t0 + beat * BEAT, db(-7)); kicks.append(t0 + beat * BEAT)
        for beat in (1, 3):
            drums.add(clap(), t0 + beat * BEAT, db(-13))
        for e in range(16):
            drums.add(hat(e % 4 == 2), t0 + e * BEAT / 4, db(-27 if e % 2 else -24), pan=0.3)
    sfx.add(whoosh(0.5, 400, 6000, 0.7), 27.55, db(-17))

    # ------------------------------------------------------------ MODULES (28-42 s)
    mods = [M_['start'] + i * M_['step'] for i in range(7)]
    for b in range(15, 22):
        t0 = bar_t(b)
        for beat in range(4):
            drums.add(kick(1.0), t0 + beat * BEAT, db(-8)); kicks.append(t0 + beat * BEAT)
        for beat in (1, 3):
            drums.add(clap(), t0 + beat * BEAT, db(-14))
        for e in range(8):
            drums.add(hat(e == 7), t0 + e * BEAT / 2, db(-26 if e % 2 else -29), pan=0.3)
        if b % 2 == 0:
            for e in range(6):
                drums.add(hat(), t0 + 3 * BEAT + e * BEAT / 6, db(-30), pan=-0.3)
    for i, a in enumerate(mods):
        sfx.add(whoosh(0.45, 600, 5000, 0.75), a - 0.47, db(-24))
        sfx.add(bell(nm(['D5', 'E5', 'F#5', 'A5', 'B5', 'D6', 'E6'][i]), 1.2), a + 0.02, db(-25), pan=0.3)
    # bruitages spécifiques
    a = mods[0]
    for k in range(6):
        sfx.add(woodblock(700 + k * 80), a + k * 0.11 + 0.3, db(-20), pan=0.3)
    sfx.add(bell(nm('A6'), 1.2), a + 0.95, db(-24))
    a = mods[1]
    sfx.add(whoosh(0.35, 1500, 5000, 0.8), a + 0.45, db(-22), pan=-0.4)
    sfx.add(woodblock(320) * 1.5, a + 0.8, db(-15), pan=0.2)
    boing = np.sin(2 * np.pi * np.cumsum(180 + 40 * np.sin(2 * np.pi * 9 * np.arange(int(0.5 * SR)) / SR)) / SR) * np.exp(-np.arange(int(0.5 * SR)) / SR / 0.12)
    sfx.add(boing, a + 0.82, db(-24))
    a = mods[2]
    for k in range(3):
        sfx.add(pop(700 + 150 * k), a + 0.45 + k * 0.28, db(-19), pan=-0.4 + 0.4 * k)
    a = mods[3]
    sfx.add(whoosh(0.7, 500, 1500, 0.9), a + 0.15, db(-26))
    sfx.add(woodblock(520) + woodblock(1040) * 0.5, a + 0.85, db(-14))
    for k in range(8):
        sfx.add(coin(), a + 0.88 + k * 0.03, db(-30), pan=RNG.uniform(-0.5, 0.5))
    a = mods[4]
    for k in range(4):
        sfx.add(pop(400 + k * 120), a + 0.1 + k * 0.12, db(-22))
    sfx.add(bell(nm('E6'), 0.8) + bell(nm('B6'), 0.8) * 0.6, a + 1.1, db(-20))
    for k in range(6):
        sfx.add(coin(), a + 0.3 + k * 0.09, db(-27))
    a = mods[5]
    for k in range(9):
        sfx.add(woodblock(500 + k * 70), a + 0.05 + k * 0.1, db(-22), pan=-0.3 + k * 0.07)
    sfx.add(whoosh(0.55, 300, 1200, 0.5), a + 0.35, db(-26))
    a = mods[6]
    for k in range(6):
        sfx.add(pop(600 + k * 90), a + 0.15 + k * 0.09, db(-22), pan=-0.5 + k * 0.2)
    music.add(pad([nm('D4'), nm('F#4'), nm('A4'), nm('E5')], 1.6, 4000, 0.4), a + 0.8, db(-24))

    # ------------------------------------------------------------ PAYOFF (42-46 s)
    P = T['payoff']
    music.add(pad([nm(x) for x in ['D3', 'A3', 'F#4', 'E4', 'A4']], 4.4, 2600, 0.15), P['start'], db(-15))
    for i, n_ in enumerate(penta_run(4, 14)):
        music.add(pluck(nm(n_), 1.6, 0.8), P['start'] + i * 0.05, db(-12), pan=-0.7 + i * 0.1)
    sfx.add(sub_boom(2.5, 50, 30), P['start'], db(-9))
    sfx.add(crash(3.0), P['start'], db(-18))
    sfx.add(bell(nm('D6'), 3.0) + bell(nm('A6'), 3.0) * 0.5, P['medal'] + 0.3, db(-19))
    for k in range(4):
        drums.add(kick(0.8), P['start'] + BAR + k * BEAT, db(-12)); kicks.append(P['start'] + BAR + k * BEAT)
    sfx.add(whoosh(1.2, 2500, 200, 0.3), 45.6, db(-17))

    # ------------------------------------------------------------ FONDATEURS, NUIT (46-56 s)
    hum_n = int(9.0 * SR)
    ht = np.arange(hum_n) / SR
    hum = filt(signal.sawtooth(2 * np.pi * 100 * ht), 'lowpass', 900) * 0.25
    flick = np.ones(hum_n)
    for k in range(10):
        i = int((0.05 + k * 0.06) * SR)
        flick[i:i + int(0.025 * SR)] = 0.1
    sfx.add(hum * flick * np.minimum(1, ht / 0.05) * np.exp(-np.maximum(0, ht - 1.2) / 2.5), F_['neon'], db(-34))
    for k in range(7):
        sfx.add(tick() * 2, F_['neon'] + 0.05 + k * 0.08, db(-24))
    for b in range(24, 29):
        t0 = bar_t(b)
        ch = PROG[b]
        for beat, vel in ((0, 1.0), (1.5, 0.7), (2.75, 0.6)):
            drums.add(kick(vel), t0 + beat * BEAT, db(-10)); kicks.append(t0 + beat * BEAT)
        drums.add(snare(), t0 + 2 * BEAT, db(-17))
        for e in range(8):
            sw = 0.04 if e % 2 else 0.0
            drums.add(hat(), t0 + e * BEAT / 2 + sw, db(-31 if e % 2 else -28), pan=0.35)
        for j, n_ in enumerate(CH[ch]):
            keys.add(epiano(nm(n_) * 2, 1.9), t0 + j * 0.012, db(-22), pan=-0.3 + j * 0.2)
        keys.add(epiano(nm(CH[ch][1]) * 4, 0.8), t0 + 2.5 * BEAT, db(-27), pan=0.4)
    vin_n = int(10.4 * SR)
    vin = crackle(10.4, 25) * 0.6 + filt(noise(vin_n), 'lowpass', 2000) * 0.05
    sfx.add(vin, 46.0, db(-30))
    for a in F_['photos']:
        sfx.add(shutter(), a + 0.38, db(-14), pan=0.3)
        sfx.add(whoosh(0.5, 3000, 600, 0.3), a, db(-27))
    traffic = filt(noise(int(10 * SR)), 'lowpass', 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.21 * np.arange(int(10 * SR)) / SR))
    sfx.add(traffic, 46.2, db(-34))

    # ------------------------------------------------------------ FINAL (56-62 s)
    Fi = T['finale']
    music.add(riser(2.4), 55.6, db(-11))
    music.add(pad([nm(x) for x in CH['A']], 2.2, 1500, 0.4), 56.0, db(-19))
    for k in range(20):
        tt = 56.6 + 1.4 * (1 - (1 - k / 20) ** 1.5)
        drums.add(snare(), tt, db(-25 + k * 0.6))
    for k, t0 in enumerate([56.4, 57.1, 57.6, 58.3, 59.0, 59.8, 60.4]):
        launch = np.sin(2 * np.pi * np.cumsum(np.linspace(600, 2400, int(0.35 * SR))) / SR) * np.linspace(0.2, 1, int(0.35 * SR)) * 0.3
        sfx.add(launch, t0 - 0.35, db(-34), pan=-0.6 + k * 0.2)
        sfx.add(filt(noise(int(0.5 * SR)), 'lowpass', 1800) * np.exp(-np.arange(int(0.5 * SR)) / SR / 0.06), t0, db(-18), pan=-0.6 + k * 0.2)
        sfx.add(crackle(1.6, 70), t0 + 0.08, db(-26), pan=-0.6 + k * 0.2)
    final = bar_t(30)
    sfx.add(sub_boom(3.0, 55, 30), final, db(-5))
    sfx.add(crash(4.0), final, db(-14))
    music.add(pad([nm(x) for x in ['D2', 'A2', 'D3', 'F#3', 'A3', 'E4', 'F#4']], 4.2, 3200, 0.05), final, db(-13))
    for i, n_ in enumerate(penta_run(4, 15)):
        music.add(pluck(nm(n_), 2.0, 0.85), final + i * 0.045, db(-11), pan=-0.7 + i * 0.1)
    sfx.add(gong(73.4, 4.0), final + 0.02, db(-18))
    st = Fi['stamp']
    sfx.add(sub_boom(1.2, 80, 40), st, db(-8))
    sfx.add(filt(noise(int(0.15 * SR)), 'bandpass', (400, 2500)) * np.exp(-np.arange(int(0.15 * SR)) / SR / 0.02), st, db(-12))
    sfx.add(woodblock(260) * 1.4, st, db(-14))

    # ------------------------------------------------------------ couches musicales continues (6-56 s)
    for b in range(4, 29):
        if b == 12:
            music.add(pad([nm(x) for x in ['A2', 'D3', 'E3', 'A3']], BAR, 700, 0.3), bar_t(b), db(-22))
            continue
        t0 = bar_t(b)
        ch = PROG[b]
        lvl = -21 if b < 7 else (-19 if b < 24 else -22)
        cutoff = 1200 if b < 7 else (2200 if b < 24 else 1400)
        music.add(pad([nm(x) for x in CH[ch]], BAR + 0.15, cutoff, 0.08), t0, db(lvl))
        if 7 <= b < 24 and b not in (22, 23):
            for e in range(8):
                bn = nm(BASS[ch]) * (2 if e in (3, 7) else 1)
                bass.add(bassnote(bn, BEAT / 2 * 0.9), t0 + e * BEAT / 2, db(-13))
        elif b >= 24:
            bass.add(bassnote(nm(BASS[ch]), BEAT * 1.8), t0, db(-14))
            bass.add(bassnote(nm(BASS[ch]) * 1.5, BEAT * 0.9), t0 + 2.5 * BEAT, db(-17))
        elif b >= 4:
            bass.add(bassnote(nm(BASS[ch]), BAR * 0.95), t0, db(-17))
    # motif guzheng : villes et modules (2 mesures par motif)
    for b in list(range(5, 11, 2)) + list(range(15, 22, 2)) + [13]:
        t0 = bar_t(b)
        for note, beat in MOTIF:
            music.add(pluck(nm(note), 1.0, 0.65), t0 + beat * BEAT, db(-14), pan=RNG.uniform(-0.3, 0.3))
    # nuit : motif plus doux, une octave plus bas
    for b in (25, 27):
        t0 = bar_t(b)
        for note, beat in MOTIF[::2]:
            music.add(pluck(nm(note) / 2, 1.6, 0.35), t0 + beat * BEAT, db(-17), pan=RNG.uniform(-0.4, 0.4))

    # ------------------------------------------------------------ mixage
    duck = np.ones(N)
    for k in kicks:
        i = int(k * SR)
        n = int(0.22 * SR)
        if i < N:
            m = min(n, N - i)
            duck[i:i + m] = np.minimum(duck[i:i + m], 1 - 0.55 * np.exp(-np.arange(m) / SR / 0.07))
    ir = reverb_ir()
    music.x *= (1 - (1 - duck) * 0.6) * db(5)
    drums.x *= db(-1.5)
    bass.x *= (0.5 + 0.5 * duck) * db(-2)
    keys.x *= 0.7 + 0.3 * duck
    wet = reverb(music.x * 0.5 + keys.x * 0.6 + sfx.x * 0.25 + drums.x * 0.06, ir, db(-8))
    mix = drums.x + bass.x + music.x * 1.0 + keys.x + sfx.x + wet
    BUSES.update(drums=drums.x, bass=bass.x, music=music.x, keys=keys.x, sfx=sfx.x, wet=wet)
    mix = np.stack([filt(c, 'highpass', 28) for c in mix])
    return mix


# ----------------------------------------------------------------------------- mastering
def k_weight(x):
    shelf = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x)
    return signal.lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], shelf)


def loudness(st):
    z = [k_weight(c) for c in st]
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    pw = np.array([sum(np.mean(zc[s:s + blk] ** 2) for zc in z) for s in range(0, st.shape[1] - blk, hop)])
    lb = -0.691 + 10 * np.log10(pw + 1e-12)
    g = pw[lb > -70]
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    return -0.691 + 10 * np.log10(pw[(lb > -70) & (lb > rel)].mean())


def true_peak(st):
    return 20 * np.log10(np.abs(signal.resample_poly(st, 4, 1, axis=1)).max() + 1e-12)


def limiter(x, ceiling=db(-1.2), release=0.08):
    """Limiteur à anticipation (5 ms) : le gain chute instantanément et remonte doucement."""
    from scipy.ndimage import maximum_filter1d
    look = int(0.005 * SR)
    peak = maximum_filter1d(np.abs(x).max(axis=0), size=2 * look + 1)
    g = np.minimum(1.0, ceiling / (peak + 1e-9))
    hop = 16
    gd = g[::hop]
    a = np.exp(-hop / (release * SR))
    out = np.empty_like(gd)
    cur = 1.0
    for i, v in enumerate(gd):
        cur = v if v < cur else a * cur + (1 - a) * v
        out[i] = cur
    env = np.interp(np.arange(len(g)), np.arange(len(gd)) * hop, out)
    return x * np.minimum(env, g)


def master(mix, target=-14.0):
    mix = mix * db(target - loudness(mix))
    for _ in range(3):
        mix = limiter(mix)
        tp = true_peak(mix)
        if tp <= -1.0:
            break
        mix *= db(-1.0 - tp - 0.1)
    t = np.arange(mix.shape[1]) / SR
    fade = np.clip((DUR - t) / 0.9, 0, 1) ** 1.5
    fade = np.where(t > T['finale']['fade'][0], fade, 1.0)
    return mix * fade * np.clip(t / 0.01, 0, 1)


def write_wav(path, st):
    x = np.clip(st.T, -1, 1)
    pcm = np.ascontiguousarray(np.round(x * (2 ** 23 - 1)).astype('<i4'))
    raw = pcm.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(raw)


if __name__ == '__main__':
    mix = master(build())
    out = os.path.join(ROOT, 'output', 'soundtrack.wav')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_wav(out, mix)
    print(f'{out}  {loudness(mix):.1f} LUFS  crête {true_peak(mix):.1f} dBTP')
