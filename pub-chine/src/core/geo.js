// Palette, matériaux et briques de modélisation (style « jouet » isométrique).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const C = {
  red: '#E2353B', redDeep: '#B3202A', redSoft: '#F06A5E',
  gold: '#F4B63F', goldLight: '#FFD27A', goldDeep: '#D99A1E',
  jade: '#2FA37C', jadeDark: '#1E7A5C', teal: '#2E6B6B', tealLight: '#4F9A94',
  ink: '#1B1E2E', navy: '#232A4D', slate: '#3D4566',
  cream: '#F7EBDD', sand: '#EAD7BE', stone: '#D9CDBD', white: '#FBF7F2', paper: '#FFFDF8',
  grass: '#8CC66A', grassDark: '#6FAE55', earth: '#B9825A', earthDark: '#8C5B3F', rock: '#6E4B3A',
  water: '#4FBEDD', waterDeep: '#2F96C2', glass: '#8FD3E8', glassDark: '#5BA9C4',
  pink: '#FF8FA3', peach: '#FFC49B', lilac: '#B7A6E8', sky: '#9FD8F2',
  asphalt: '#3A3F55', asphaltNight: '#2A2E44',
  neonPink: '#FF3D9A', neonCyan: '#29F0E4', neonOrange: '#FF8A2A', neonYellow: '#FFE45C',
};

const matCache = new Map();
/** Matériau satiné standard, mis en cache. */
export function mat(color, opts = {}) {
  const key = color + JSON.stringify(opts);
  if (matCache.has(key)) return matCache.get(key);
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.62, metalness: 0.0, ...opts });
  matCache.set(key, m);
  return m;
}

/** Matériau émissif dont l'intensité suit la nuit (enregistré pour pilotage global). */
export const glowMats = [];
export function glow(color, base = 0.0, night = 2.2, opts = {}) {
  const m = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: base, roughness: 0.4, ...opts });
  m.userData.glow = { base, night };
  glowMats.push(m);
  return m;
}
export function setNight(k) {
  for (const m of glowMats) m.emissiveIntensity = THREE.MathUtils.lerp(m.userData.glow.base, m.userData.glow.night, k);
}

const geoCache = new Map();
export function rbox(w, h, d, r = 0.08, s = 2) {
  const key = `${w}|${h}|${d}|${r}|${s}`;
  if (!geoCache.has(key)) geoCache.set(key, new RoundedBoxGeometry(w, h, d, s, Math.min(r, w / 2.01, h / 2.01, d / 2.01)));
  return geoCache.get(key);
}
export function cyl(rt, rb, h, n = 20) {
  const key = `cyl|${rt}|${rb}|${h}|${n}`;
  if (!geoCache.has(key)) geoCache.set(key, new THREE.CylinderGeometry(rt, rb, h, n));
  return geoCache.get(key);
}
export function sph(r, n = 20) {
  const key = `sph|${r}|${n}`;
  if (!geoCache.has(key)) geoCache.set(key, new THREE.SphereGeometry(r, n, Math.max(8, n * 0.75 | 0)));
  return geoCache.get(key);
}

export function mesh(geo, material, { cast = true, receive = true } = {}) {
  const m = new THREE.Mesh(geo, material);
  m.castShadow = cast;
  m.receiveShadow = receive;
  return m;
}

/** Ajoute un objet dans un groupe, avec position / rotation / échelle. */
export function put(parent, obj, x = 0, y = 0, z = 0, ry = 0, s = 1) {
  obj.position.set(x, y, z);
  obj.rotation.y = ry;
  if (typeof s === 'number') obj.scale.setScalar(s); else obj.scale.set(...s);
  parent.add(obj);
  return obj;
}

/** Pivot placé au sol : l'objet pousse vers le haut quand on anime scale.y. */
export function grower(child, x = 0, z = 0, y = 0) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  g.add(child);
  return g;
}

/** Île flottante : dalle d'herbe + strates de terre, coins arrondis. */
export function islandBase(w, d, { top = C.grass, layers = [C.earth, C.earthDark, C.rock], h = [0.5, 1.2, 1.0, 0.8] } = {}) {
  const g = new THREE.Group();
  let y = 0;
  const topM = mesh(rbox(w, h[0], d, 0.25, 3), mat(top, { roughness: 0.85 }));
  topM.position.y = -h[0] / 2;
  g.add(topM);
  y = -h[0];
  layers.forEach((c, i) => {
    const inset = 0.25 * (i + 1);
    const hh = h[i + 1] ?? 0.8;
    const m = mesh(rbox(w - inset * 2, hh, d - inset * 2, 0.22, 2), mat(c, { roughness: 0.95 }));
    m.position.y = y - hh / 2 + 0.02;
    g.add(m);
    y -= hh;
  });
  g.userData.depth = -y;
  return g;
}

/** Texture de fenêtres (canvas) pour façades, avec carte émissive pour la nuit. */
const winTex = new Map();
export function windowTexture(cols, rows, { frame = '#EFE6DA', pane = '#7FB7CF', lit = '#FFD98A', seed = 1, litRatio = 0.55 } = {}) {
  const key = [cols, rows, frame, pane, lit, seed].join('|');
  if (winTex.has(key)) return winTex.get(key);
  const cw = 32 * cols, ch = 32 * rows;
  const mk = () => { const c = document.createElement('canvas'); c.width = cw; c.height = ch; return c; };
  const cA = mk(), cE = mk();
  const a = cA.getContext('2d'), e = cE.getContext('2d');
  a.fillStyle = frame; a.fillRect(0, 0, cw, ch);
  e.fillStyle = '#000'; e.fillRect(0, 0, cw, ch);
  let s = seed * 9301 + 49297;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
    const x = i * 32 + 6, y = j * 32 + 6;
    a.fillStyle = pane; a.fillRect(x, y, 20, 20);
    if (rnd() < litRatio) { e.fillStyle = lit; e.fillRect(x, y, 20, 20); }
  }
  const tA = new THREE.CanvasTexture(cA), tE = new THREE.CanvasTexture(cE);
  tA.colorSpace = THREE.SRGBColorSpace; tE.colorSpace = THREE.SRGBColorSpace;
  tA.anisotropy = 4;
  const r = { map: tA, emissiveMap: tE };
  winTex.set(key, r);
  return r;
}

/** Façade avec fenêtres qui s'allument la nuit. */
export function windowMat(cols, rows, opts = {}) {
  const { map, emissiveMap } = windowTexture(cols, rows, opts);
  const m = new THREE.MeshStandardMaterial({ map, emissiveMap, emissive: '#ffffff', emissiveIntensity: 0, roughness: 0.55 });
  m.userData.glow = { base: 0, night: opts.night ?? 0.9 };
  glowMats.push(m);
  return m;
}

/** Texte peint sur une texture (enseignes, panneaux). */
export function textTexture(text, { font = '700 120px "Barlow Condensed"', color = '#fff', bg = null, w = 512, h = 256, pad = 0, stroke = null } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  if (bg) { g.fillStyle = bg; g.fillRect(0, 0, w, h); }
  g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle';
  if (stroke) { g.lineWidth = stroke.width; g.strokeStyle = stroke.color; g.strokeText(text, w / 2, h / 2 + pad); }
  g.fillStyle = color; g.fillText(text, w / 2, h / 2 + pad);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

/** Instanciation simple : liste de matrices -> InstancedMesh. */
export function instanced(geo, material, matrices, { cast = true, receive = true } = {}) {
  const im = new THREE.InstancedMesh(geo, material, matrices.length);
  matrices.forEach((m, i) => im.setMatrixAt(i, m));
  im.castShadow = cast;
  im.receiveShadow = receive;
  im.instanceMatrix.needsUpdate = true;
  return im;
}

export const M4 = new THREE.Matrix4();
export const Q = new THREE.Quaternion();
export const V = new THREE.Vector3();
export const S = new THREE.Vector3();
export function compose(x, y, z, ry = 0, sx = 1, sy = 1, sz = 1, rx = 0, rz = 0) {
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz));
  m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(sx, sy, sz));
  return m;
}

/** Cylindre tendu entre deux points (pieds, câbles, liens lumineux). */
const _up = new THREE.Vector3(0, 1, 0);
export function beam(p0, p1, r, material, n = 8) {
  const a = new THREE.Vector3(...p0), b = new THREE.Vector3(...p1);
  const d = b.clone().sub(a);
  const len = d.length();
  const m = mesh(cyl(r, r, 1, n), material);
  m.scale.set(1, len, 1);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.quaternion.setFromUnitVectors(_up, d.normalize());
  return m;
}

/** Révolution d'un profil avec dégradé de couleur bas -> haut (montagnes, vases...). */
export function latheGrad(points, colBot, colTop, n = 18) {
  const g = new THREE.LatheGeometry(points.map(([x, y]) => new THREE.Vector2(x, y)), n);
  const pos = g.attributes.position;
  let ymin = Infinity, ymax = -Infinity;
  for (let i = 0; i < pos.count; i++) { ymin = Math.min(ymin, pos.getY(i)); ymax = Math.max(ymax, pos.getY(i)); }
  const cb = new THREE.Color(colBot), ct = new THREE.Color(colTop), c = new THREE.Color();
  const cols = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const k = (pos.getY(i) - ymin) / (ymax - ymin || 1);
    c.copy(cb).lerp(ct, Math.pow(k, 0.9));
    cols.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(cols, 3));
  g.computeVertexNormals();
  return g;
}

/** Inscrit un matériau existant au pilotage jour/nuit. */
export function registerGlow(m, base, night) {
  m.userData.glow = { base, night };
  glowMats.push(m);
  return m;
}
