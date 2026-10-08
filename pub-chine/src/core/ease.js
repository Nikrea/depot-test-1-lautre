// Courbes d'animation, interpolation de clés et hasard reproductible.
// Tout est fonction du temps t (secondes) : aucune image ne dépend de la précédente.

export const clamp = (x, a = 0, b = 1) => Math.min(Math.max(x, a), b);
export const lerp = (a, b, t) => a + (b - a) * t;
export const seg = (t, a, b) => clamp((t - a) / (b - a));
export const smooth = (x) => x * x * (3 - 2 * x);
export const smoother = (x) => x * x * x * (x * (x * 6 - 15) + 10);

export const inQuad = (x) => x * x;
export const outQuad = (x) => 1 - (1 - x) * (1 - x);
export const inCubic = (x) => x * x * x;
export const outCubic = (x) => 1 - Math.pow(1 - x, 3);
export const inOutCubic = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const outQuart = (x) => 1 - Math.pow(1 - x, 4);
export const inQuart = (x) => x * x * x * x;
export const inOutQuart = (x) => (x < 0.5 ? 8 * x ** 4 : 1 - Math.pow(-2 * x + 2, 4) / 2);
export const outQuint = (x) => 1 - Math.pow(1 - x, 5);
export const inOutQuint = (x) => (x < 0.5 ? 16 * x ** 5 : 1 - Math.pow(-2 * x + 2, 5) / 2);
export const outExpo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
export const inExpo = (x) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10));
export const inOutExpo = (x) =>
  x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2;
export const inOutSine = (x) => -(Math.cos(Math.PI * x) - 1) / 2;
export const outSine = (x) => Math.sin((x * Math.PI) / 2);

export function outBack(x, s = 1.70158) {
  const c3 = s + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
}
export function inBack(x, s = 1.70158) {
  return (s + 1) * x * x * x - s * x * x;
}
export function outElastic(x, p = 0.32) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  return Math.pow(2, -10 * x) * Math.sin(((x - p / 4) * (2 * Math.PI)) / p) + 1;
}
export function outBounce(x) {
  const n1 = 7.5625, d1 = 2.75;
  if (x < 1 / d1) return n1 * x * x;
  if (x < 2 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
  if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
  return n1 * (x -= 2.625 / d1) * x + 0.984375;
}

/** Ressort sous-amorti : 0 -> 1 avec dépassement. */
export function spring(tau, zeta = 0.45, omega = 14) {
  if (tau <= 0) return 0;
  const wd = omega * Math.sqrt(1 - zeta * zeta);
  const e = Math.exp(-zeta * omega * tau);
  return 1 - e * (Math.cos(wd * tau) + ((zeta * omega) / wd) * Math.sin(wd * tau));
}

/** Oscillation amortie (secousse, rebond résiduel). */
export const damped = (tau, f = 6, decay = 6) => (tau <= 0 ? 0 : Math.exp(-decay * tau) * Math.sin(2 * Math.PI * f * tau));

/** Impulsion rapide (attaque, puis décroissance). */
export const pulse = (tau, a = 0.03, d = 0.25) => (tau <= 0 ? 0 : (1 - Math.exp(-tau / a)) * Math.exp(-tau / d));

/** Apparition / disparition en fondu sur une fenêtre [a, b]. */
export function window01(t, a, b, fin = 0.25, fout = 0.25, easeIn = outCubic, easeOut = inCubic) {
  if (t < a || t > b) return 0;
  const i = easeIn(seg(t, a, a + fin));
  const o = 1 - easeOut(seg(t, b - fout, b));
  return Math.min(i, o);
}

/** Interpolation cubique monotone (Fritsch-Carlson) : vitesse continue, pas de dépassement. */
export function pchip(keys) {
  const x = keys.map((k) => k[0]);
  const y = keys.map((k) => k[1]);
  const n = x.length;
  const h = [], d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) {
    h.push(x[i + 1] - x[i]);
    d.push((y[i + 1] - y[i]) / (x[i + 1] - x[i]));
  }
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] > 0) {
      const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
      m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
    }
  }
  return (t) => {
    if (t <= x[0]) return y[0];
    if (t >= x[n - 1]) return y[n - 1];
    let i = 0;
    while (i < n - 2 && t > x[i + 1]) i++;
    const u = (t - x[i]) / h[i];
    const h00 = 2 * u ** 3 - 3 * u ** 2 + 1, h10 = u ** 3 - 2 * u ** 2 + u;
    const h01 = -2 * u ** 3 + 3 * u ** 2, h11 = u ** 3 - u ** 2;
    return h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1];
  };
}

/** Piste à segments : [[t, v, ease?], ...] — l'easing de la clé i s'applique vers la clé i+1. */
export function track(keys) {
  return (t) => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 0; i < keys.length - 1; i++) {
      const [t0, v0, e] = keys[i];
      const [t1, v1] = keys[i + 1];
      if (t <= t1) {
        const u = (e || inOutCubic)(seg(t, t0, t1));
        return Array.isArray(v0) ? v0.map((a, j) => lerp(a, v1[j], u)) : lerp(v0, v1, u);
      }
    }
    return keys[keys.length - 1][1];
  };
}

/** Générateur pseudo-aléatoire déterministe. */
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Bruit lisse 1D (somme de sinus déphasés). */
export const wobble = (t, seed = 0, f = 1) =>
  0.5 * Math.sin(t * 1.7 * f + seed * 12.9) + 0.3 * Math.sin(t * 2.9 * f + seed * 4.1) + 0.2 * Math.sin(t * 5.3 * f + seed * 7.7);
