"""L'AUTRE — sound design de l'intro, synthétisé et calé sur la timeline de render.py.

Couches :
  - souffle de salle + drone grave (ré)                      : l'obscurité
  - battements de cœur « lub-dub »                            : la lumière s'allume au premier
  - plume sur papier, modulée par l'écriture réelle           : la phrase manuscrite
  - nappe (ré, la, mi) qui s'ouvre en ré majeur add9          : la mise au point, puis le nom
  - montée de tension + étirement élastique                   : le pont de matière s'étire
  - goutte + impact sub + cloche lumineuse                    : l'apostrophe se détache
  - sept notes pentatoniques, une par lettre                   : L'AUTRE s'allume
  - refroidissement du filament (glissando + petits « tics »)  : la lumière s'éteint

Usage : python3 intro/audio.py  ->  output/intro_audio.wav (48 kHz, 24 bits, stéréo)
"""
from __future__ import annotations

import os
import sys
import wave

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

SR = 48000
DUR = R.DURATION
N = int(round(DUR * SR))
T = np.arange(N) / SR
RNG = np.random.default_rng(2024)


# ----------------------------------------------------------------- outils
def db(x):
    return 10 ** (x / 20)


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x, axis=-1)


def noise(n=N):
    return RNG.standard_normal(n)


def env_exp(t0, attack, decay, t=T):
    tau = t - t0
    e = np.where(tau >= 0, (1 - np.exp(-np.maximum(tau, 0) / max(attack, 1e-4))) * np.exp(-np.maximum(tau, 0) / decay), 0.0)
    return e


def ramp(t0, t1, t=T):
    return np.clip((t - t0) / (t1 - t0), 0, 1)


def smooth_ramp(t0, t1, t=T):
    x = ramp(t0, t1, t)
    return x * x * (3 - 2 * x)


def pan(mono, p):
    """p dans [-1, 1] (scalaire ou tableau), loi à puissance constante."""
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)])


def sine_glide(f_of_t, t=T, phase=0.0):
    ph = 2 * np.pi * np.cumsum(f_of_t) / SR + phase
    return np.sin(ph)


def saw_soft(freq, t=T, harmonics=18):
    """Dent de scie à bande limitée, adoucie (harmoniques en 1/n^1.4)."""
    out = np.zeros_like(t)
    for n in range(1, harmonics + 1):
        if freq * n > 9000:
            break
        out += np.sin(2 * np.pi * freq * n * t + RNG.uniform(0, 6.28)) / n ** 1.4
    return out


def reverb_ir(rt60=2.8, length=3.4, predelay=0.025, damp=0.55, seed=5):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    tau = rt60 / 6.91
    ir = np.zeros((2, n + int(predelay * SR)))
    for c in range(2):
        nz = rng.standard_normal(n)
        lo = filt(nz, "lowpass", 1800) * np.exp(-t / tau)
        hi = filt(nz, "highpass", 1800) * np.exp(-t / (tau * damp))
        tail = (lo + 0.6 * hi) * (1 - np.exp(-t / 0.012))
        # premières réflexions éparses
        for _ in range(9):
            k = int(rng.uniform(0.004, 0.075) * SR)
            tail[k] += rng.uniform(-1, 1) * 2.5
        ir[c, int(predelay * SR):] = tail
    ir /= np.sqrt((ir ** 2).sum() / 2)
    return ir


IR = reverb_ir()


def reverb(st, wet=1.0):
    out = np.stack([signal.fftconvolve(st[c], IR[c])[:N] for c in range(2)])
    return out * wet


def mono_to_st(m):
    return np.stack([m, m]) * np.sqrt(0.5)


# ----------------------------------------------------------------- couches
def room_tone():
    nz = filt(noise(), "lowpass", 1400) + 0.3 * filt(noise(), "lowpass", 300)
    e = smooth_ramp(0.0, 0.6) * (1 - smooth_ramp(9.15, 9.58))
    a = np.stack([nz, filt(noise(), "lowpass", 1400)]) * e
    return a * db(-50)


def drone():
    f = 36.71                      # ré 1
    x = (np.sin(2 * np.pi * f * T) + 0.55 * np.sin(2 * np.pi * 2 * f * T + 0.3)
         + 0.35 * np.sin(2 * np.pi * 1.5 * 2 * f * T + 1.1))        # ré, ré, la
    x = np.tanh(1.8 * x) * 0.7                                      # harmoniques audibles sur petits HP
    build = 0.35 + 0.65 * smooth_ramp(0.2, R.SNAP_T) - 0.4 * smooth_ramp(R.SNAP_T + 0.3, R.SNAP_T + 2.5)
    e = smooth_ramp(0.15, 1.6) * build * (1 - smooth_ramp(8.55, 9.45))
    e *= 1 + 0.08 * np.sin(2 * np.pi * 0.21 * T)
    return mono_to_st(filt(x, "lowpass", 400) * e) * db(-20)


def heartbeat():
    out = np.zeros(N)
    for i, b in enumerate(R.BEATS):
        for k, (dt, amp) in enumerate(((0.0, 1.0), (0.23, 0.62))):
            t0 = b + dt
            tau = T - t0
            f = 44 + 34 * np.exp(-np.maximum(tau, 0) / 0.035)
            body = sine_glide(f) * env_exp(t0, 0.004, 0.16)
            click = filt(noise(), "bandpass", (90, 520)) * env_exp(t0, 0.001, 0.018)
            lvl = (1.0 if i == 0 else 0.85) * amp
            out += (body + 0.35 * click) * lvl
    out = np.tanh(out * 1.6) / 1.2
    return mono_to_st(out) * db(-13)


def writing_activity():
    """Activité de la plume (pixels de trait révélés par unité de temps)."""
    d = R.DATA
    trev = R.build_trev()
    stroke = d["T_sdf"] < 0
    times = trev[stroke]
    times = times[times < 50]
    hist, edges = np.histogram(times, bins=int(DUR * 200), range=(0, DUR))
    act = np.convolve(hist.astype(float), np.hanning(7) / np.hanning(7).sum(), mode="same")
    act /= act.max()
    centers = (edges[:-1] + edges[1:]) / 2
    return np.interp(T, centers, act)


def pen():
    act = writing_activity()
    act = np.clip(act * 1.6, 0, 1) ** 0.8
    grain = np.abs(filt(noise(), "lowpass", 60)) * 3.0          # fibres du papier
    scratch = filt(noise(), "bandpass", (1800, 7500), order=2) * (0.55 + 0.45 * np.clip(grain, 0, 1.5))
    body = filt(noise(), "bandpass", (500, 1400)) * 0.35
    x = (scratch + body) * act
    # étincelles de lumière à la pointe : partiels aigus très discrets
    spark = (np.sin(2 * np.pi * 2637 * T) + 0.6 * np.sin(2 * np.pi * 3951 * T)) * act * 0.05
    p = -0.05 + 0.55 * ramp(R.LINE1[0], R.LINE2[1])              # la plume avance vers la droite
    return pan(x + spark, p) * db(-23)


def pad():
    """Nappe : quinte ouverte ré-la + neuvième (mi), puis fa# et la aigu
    pour s'ouvrir en ré majeur add9 quand le nom apparaît."""
    out = np.zeros((2, N))
    voices = [(73.42, 0.0, 1.0), (110.0, 0.0, 0.8), (146.83, 0.0, 0.55), (164.81, 1.2, 0.35),
              (220.0, 2.6, 0.30), (185.0, R.WORD - 0.15, 0.42), (329.63, R.WORD, 0.20), (440.0, R.WORD + 0.25, 0.14)]
    for i, (f, t_in, amp) in enumerate(voices):
        v = np.zeros(N)
        for det in (-0.004, 0.0, 0.0047):
            v += saw_soft(f * (1 + det))
        e = smooth_ramp(max(t_in, 0.55), max(t_in, 0.55) + (2.4 if t_in < 3 else 0.9))
        lr = pan(v * e * amp, np.sin(i * 1.7) * 0.5)
        out += lr
    # filtre qui s'ouvre avec la mise au point, se ferme à l'extinction
    cutoff_open = smooth_ramp(3.7, R.SNAP_T + 0.4)
    close = smooth_ramp(8.4, 9.5)
    res = np.zeros_like(out)
    edges = np.linspace(0, N, 97).astype(int)
    zi = None
    for a, b in zip(edges[:-1], edges[1:]):
        tm = (a + b) / 2 / SR
        fc = 380 + 2600 * float(np.interp(tm, T, cutoff_open)) ** 1.5
        fc *= 1 - 0.85 * float(np.interp(tm, T, close))
        s = sos("lowpass", max(fc, 90))
        if zi is None:
            zi = np.zeros((2, s.shape[0], 2))
        for c in range(2):
            res[c, a:b], zi[c] = signal.sosfilt(s, out[c, a:b], zi=zi[c])
    e = (1 - smooth_ramp(8.6, 9.5)) * (0.75 + 0.25 * smooth_ramp(R.WORD - 0.2, R.WORD + 0.6))
    return res * e * db(-30)


def riser():
    """Souffle filtré qui monte du grave à l'aigu jusqu'à la rupture."""
    t0, t1 = 3.7, R.SNAP_T
    prog = ramp(t0, t1)
    centers = np.geomspace(250, 7000, 14)
    out = np.zeros(N)
    c_now = np.log(250) + (np.log(7000) - np.log(250)) * prog ** 1.6
    for c in centers:
        band = filt(noise(), "bandpass", (c / 1.25, c * 1.25))
        w = np.exp(-0.5 * ((np.log(c) - c_now) / 0.45) ** 2)
        out += band * w
    amp = prog ** 2.2 * (T < t1)
    tail = np.where(T >= t1, np.exp(-(T - t1) / 0.04), 0.0)
    out = out * (amp + tail * amp.max())
    tone = sine_glide(220 * 2 ** (prog ** 1.4)) + 0.5 * sine_glide(330 * 2 ** (prog ** 1.4))
    tone *= prog ** 3 * (T < t1) * (1 + 0.5 * np.sin(2 * np.pi * (4 + 14 * prog) * T)) * 0.25
    st = np.stack([out + tone, filt(noise(), "bandpass", (300, 6000)) * amp * 0.25 + out * 0.9 + tone])
    return st * db(-19)


def stretch():
    """Tension élastique du pont de matière (vibrato qui se resserre)."""
    t0, t1 = R.STRETCH[0], R.SNAP_T
    prog = ramp(t0, t1)
    f = 140 + 120 * prog ** 1.5 + 9 * np.sin(2 * np.pi * (5 + 16 * prog) * T)
    x = sine_glide(f) + 0.4 * sine_glide(f * 2.01)
    x = np.tanh(2.5 * x)
    x = filt(x, "bandpass", (120, 1600))
    e = smooth_ramp(t0, t0 + 0.12) * (T < t1) * (0.4 + 0.6 * prog)
    return pan(x * e, 0.15) * db(-31)


def snap():
    t0 = R.SNAP_T
    tau = T - t0
    on = tau >= 0
    # goutte : glissando ascendant très bref (son de goutte d'eau)
    fd = 380 * np.exp(np.clip(tau, 0, 0.05) / 0.028)
    drop = sine_glide(np.where(on, fd, 380)) * env_exp(t0, 0.0015, 0.055)
    # impact sub qui descend
    fs = 30 + 30 * np.exp(-np.maximum(tau, 0) / 0.35)
    sub = np.tanh(1.5 * sine_glide(fs)) * env_exp(t0, 0.003, 0.85)
    thump = filt(noise(), "lowpass", 700) * env_exp(t0, 0.001, 0.07)
    air = filt(noise(), "bandpass", (1500, 9000)) * env_exp(t0, 0.002, 0.18)
    # cloche lumineuse (partiels légèrement inharmoniques)
    bell = np.zeros(N)
    for f, a, dcy in ((587.33, 1.0, 2.2), (880.0, 0.7, 1.8), (1318.5, 0.45, 1.3), (1760.0 * 1.003, 0.3, 0.9),
                      (2637.0 * 1.006, 0.18, 0.6)):
        bell += a * np.sin(2 * np.pi * f * T + RNG.uniform(0, 6)) * env_exp(t0 + 0.01, 0.006, dcy)
    low = mono_to_st(sub) * db(-5) + mono_to_st(thump) * db(-14)
    bright = (np.stack([drop * 0.9, drop * 1.0]) * db(-13)
              + np.stack([air, filt(noise(), "bandpass", (1500, 9000)) * env_exp(t0, 0.002, 0.18)]) * db(-24)
              + pan(bell, 0.2) * db(-25))
    return low, bright


def letters():
    """Une note par lettre de L'AUTRE (pentatonique de ré), de gauche à droite."""
    notes = [587.33, 659.25, 739.99, 880.0, 987.77, 1174.66, 1318.51]
    out = np.zeros((2, N))
    n = int(R.DATA["W_n"])
    for j in range(n):
        t0 = R.WORD + j * R.WORD_STAGGER + 0.03
        f = notes[j % len(notes)]
        x = (np.sin(2 * np.pi * f * T) + 0.25 * np.sin(2 * np.pi * 2 * f * T + 0.5)
             + 0.08 * np.sin(2 * np.pi * 3 * f * T)) * env_exp(t0, 0.004, 0.42)
        p = -0.45 + 0.9 * j / max(n - 1, 1)
        out += pan(x, p) * (0.9 if j else 1.0)
    swell = filt(noise(), "bandpass", (400, 3000)) * smooth_ramp(R.WORD - 0.45, R.WORD + 0.05) * (T < R.WORD + 0.08)
    return out * db(-27) + mono_to_st(swell) * db(-36)


def cooling():
    t0, t1 = R.FADE
    prog = ramp(t0, t1)
    glide = sine_glide(170 * 2 ** (-1.4 * prog)) * smooth_ramp(t0, t0 + 0.15) * (1 - smooth_ramp(t1 - 0.2, t1 + 0.1))
    glide = filt(np.tanh(1.5 * glide), "lowpass", 900)
    ticks = np.zeros(N)
    for tt, a in ((t0 + 0.32, 1.0), (t0 + 0.55, 0.6), (t0 + 0.71, 0.45)):
        ticks += filt(noise(), "bandpass", (3500, 9000)) * env_exp(tt, 0.0005, 0.006) * a
    return mono_to_st(glide) * db(-31) + pan(ticks, 0.1) * db(-27)


# ----------------------------------------------------------------- mastering
def k_weight(x):
    # ITU-R BS.1770 (coefficients 48 kHz) : pré-filtre (shelf aigu) + RLB (passe-haut)
    shelf = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285],
                           [1.0, -1.69065929318241, 0.73248077421585], x)
    return signal.lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], shelf)


def loudness(st):
    z = [k_weight(c) for c in st]
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    pw = []
    for s in range(0, st.shape[1] - blk, hop):
        pw.append(sum(np.mean(zc[s:s + blk] ** 2) for zc in z))
    pw = np.array(pw)
    l_blk = -0.691 + 10 * np.log10(pw + 1e-12)
    g = pw[l_blk > -70]
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = pw[(l_blk > -70) & (l_blk > rel)]
    return -0.691 + 10 * np.log10(g.mean())


def true_peak(st):
    up = signal.resample_poly(st, 4, 1, axis=1)
    return 20 * np.log10(np.abs(up).max() + 1e-12)


def master(mix, target_lufs=-15.0, ceiling_db=-1.0):
    mix = filt(mix, "highpass", 24)
    lufs = loudness(mix)
    mix = mix * db(target_lufs - lufs)
    # limiteur doux : compression des crêtes au-dessus du plafond
    c = db(ceiling_db - 0.3)
    mix = np.where(np.abs(mix) > c * 0.7, np.sign(mix) * (c * 0.7 + c * 0.3 * np.tanh((np.abs(mix) - c * 0.7) / (c * 0.3))), mix)
    tp = true_peak(mix)
    if tp > ceiling_db:
        mix *= db(ceiling_db - tp)
    # fondu de sécurité aux extrémités
    f = np.minimum(1, np.minimum(T / 0.01, (DUR - T) / 0.03))
    return mix * np.clip(f, 0, 1)


def write_wav(path, st):
    x = np.clip(st.T, -1, 1)
    pcm = np.ascontiguousarray(np.round(x * (2 ** 23 - 1)).astype("<i4"))
    raw = pcm.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)


def layers_all():
    low, bright = snap()
    return {
        "room": room_tone(), "drone": drone(), "heart": heartbeat(), "pen": pen(), "pad": pad(),
        "riser": riser(), "stretch": stretch(), "snap_lo": low, "snap_hi": bright, "letters": letters(),
        "cool": cooling(),
    }


def build(path=None):
    R.init_data()
    R.SNAP_T = R.find_snap_time()
    layers = layers_all()
    dry = sum(layers.values())
    send = (layers["heart"] * 0.30 + layers["pen"] * 0.5 + layers["pad"] * 0.6 + layers["riser"] * 0.5
            + layers["snap_hi"] * 0.6 + layers["letters"] * 0.9 + layers["cool"] * 0.6 + layers["stretch"] * 0.4)
    wet = reverb(send) * db(-9)
    mix = master(dry + wet)
    path = path or os.path.join(R.assets.ROOT, "output", "intro_audio.wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_wav(path, mix)
    print(f"audio : {path}  |  {loudness(mix):.1f} LUFS  |  crête {true_peak(mix):.1f} dBTP  |  rupture {R.SNAP_T:.3f} s")
    return path


if __name__ == "__main__":
    build()
