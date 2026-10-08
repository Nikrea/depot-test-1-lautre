// Bibliothèque de modèles procéduraux (style jouet) : architecture chinoise, ville moderne, nature, personnages.
import * as THREE from 'three';
import { C, mat, glow, rbox, cyl, sph, mesh, windowMat, textTexture, beam, latheGrad, registerGlow } from '../core/geo.js';

const vcol = (color) => new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, color });

// ------------------------------------------------------------------ repères urbains
export function pearlTower() {
  const g = new THREE.Group();
  const white = mat(C.white, { roughness: 0.5 });
  const pearl = glow(C.red, 0.05, 1.3, { roughness: 0.35, metalness: 0.1 });
  const pink = glow('#F27A8A', 0.05, 1.2, { roughness: 0.35 });
  for (let k = 0; k < 3; k++) {
    const a = (k * Math.PI * 2) / 3 + 0.4;
    g.add(beam([Math.cos(a) * 2.0, 0, Math.sin(a) * 2.0], [Math.cos(a) * 0.35, 2.9, Math.sin(a) * 0.35], 0.2, white, 10));
    g.add(beam([Math.cos(a) * 0.4, 0, Math.sin(a) * 0.4], [Math.cos(a) * 0.4, 9.2, Math.sin(a) * 0.4], 0.16, white, 10));
  }
  const s1 = mesh(sph(1.35, 28), pearl); s1.position.y = 3.6; g.add(s1);
  const s2 = mesh(sph(0.95, 24), pearl); s2.position.y = 8.6; g.add(s2);
  const s3 = mesh(sph(0.42, 18), pink); s3.position.y = 10.5; g.add(s3);
  for (const y of [5.6, 6.6, 7.4]) { const r = mesh(sph(0.3, 14), pink); r.position.y = y; g.add(r); }
  g.add(beam([0, 9.4, 0], [0, 10.2, 0], 0.18, white));
  const sp1 = mesh(cyl(0.05, 0.16, 2.6, 10), white); sp1.position.y = 12.1; g.add(sp1);
  const base = mesh(rbox(4.6, 0.3, 4.6, 0.12), mat(C.stone)); base.position.y = 0.15; g.add(base);
  g.userData.top = 13.3;
  return g;
}

export function twistTower(H = 13) {
  const g = new THREE.Group();
  const n = 22, h = H / n;
  const glass = mat('#9FD6E6', { roughness: 0.22, metalness: 0.25 });
  const band = glow(C.white, 0.0, 0.9, { roughness: 0.4 });
  for (let i = 0; i < n; i++) {
    const k = i / (n - 1);
    const s = THREE.MathUtils.lerp(3.2, 1.5, Math.pow(k, 1.2));
    const m = mesh(rbox(s, h * 0.86, s, 0.22), i % 4 === 3 ? band : glass);
    m.position.y = i * h + h / 2;
    m.rotation.y = i * 0.085;
    g.add(m);
  }
  const crown = mesh(rbox(1.3, 0.8, 1.3, 0.3), mat(C.white));
  crown.position.y = H + 0.3; crown.rotation.y = n * 0.085; g.add(crown);
  g.userData.top = H + 0.8;
  return g;
}

export function glassTower(w, d, h, { frame = '#E9F1F4', pane = '#6FA9C4', cap = C.white, seed = 1 } = {}) {
  const g = new THREE.Group();
  const cols = Math.max(2, Math.round(w * 2)), rows = Math.max(2, Math.round(h * 1.6));
  const body = mesh(rbox(w, h, d, 0.16), windowMat(cols, rows, { frame, pane, seed }));
  body.position.y = h / 2; g.add(body);
  const roof = mesh(rbox(w * 0.98, 0.3, d * 0.98, 0.12), mat(cap)); roof.position.y = h + 0.1; g.add(roof);
  const box = mesh(rbox(w * 0.4, 0.5, d * 0.4, 0.1), mat(C.stone)); box.position.y = h + 0.45; g.add(box);
  g.userData.top = h + 0.7;
  return g;
}

export function telecomTower(H = 11) {
  const g = new THREE.Group();
  const white = mat(C.white), red = mat(C.red);
  for (let i = 0; i < 6; i++) {
    const y0 = (i * H * 0.8) / 6, y1 = ((i + 1) * H * 0.8) / 6;
    const r0 = THREE.MathUtils.lerp(0.55, 0.22, i / 6), r1 = THREE.MathUtils.lerp(0.55, 0.22, (i + 1) / 6);
    const m = mesh(cyl(r1, r0, y1 - y0, 14), i % 2 ? red : white);
    m.position.y = (y0 + y1) / 2; g.add(m);
  }
  const deck = mesh(cyl(0.9, 0.7, 0.5, 20), white); deck.position.y = H * 0.62; g.add(deck);
  for (const [y, a] of [[H * 0.55, 0.6], [H * 0.68, 2.6]]) {
    const dish = mesh(new THREE.SphereGeometry(0.55, 16, 8, 0, Math.PI * 2, 0, 1.0), mat(C.stone, { side: THREE.DoubleSide }));
    dish.position.set(Math.cos(a) * 0.6, y, Math.sin(a) * 0.6); dish.rotation.z = Math.PI / 2; dish.rotation.y = -a; g.add(dish);
  }
  const ant = mesh(cyl(0.03, 0.08, H * 0.25, 8), white); ant.position.y = H * 0.8 + H * 0.125; g.add(ant);
  const tip = mesh(sph(0.12, 10), glow('#FF4040', 1.5, 3.0)); tip.position.y = H * 1.05; g.add(tip);
  g.userData.top = H * 1.05;
  return g;
}

// ------------------------------------------------------------------ architecture traditionnelle
function roof(w, d, h, color, gold = true) {
  const g = new THREE.Group();
  const geo = new THREE.ConeGeometry(Math.hypot(w, d) / 2, h, 4, 1);
  geo.rotateY(Math.PI / 4);
  const m = mesh(geo, mat(color, { roughness: 0.55 }));
  m.scale.set(w / Math.hypot(w, d) * Math.SQRT2, 1, d / Math.hypot(w, d) * Math.SQRT2);
  m.position.y = h / 2; g.add(m);
  const eave = mesh(rbox(w * 1.02, 0.08, d * 1.02, 0.03), mat(gold ? C.gold : color)); eave.position.y = 0.04; g.add(eave);
  return g;
}

export function pagoda(tiers = 5) {
  const g = new THREE.Group();
  const base = mesh(rbox(3.8, 0.45, 3.8, 0.12), mat(C.stone)); base.position.y = 0.22; g.add(base);
  let y = 0.45;
  for (let i = 0; i < tiers; i++) {
    const s = 2.5 - i * 0.32, h = 0.85 - i * 0.04;
    const wall = mesh(rbox(s, h, s, 0.06), mat('#C8312F', { roughness: 0.6 })); wall.position.y = y + h / 2; g.add(wall);
    const win = mesh(rbox(s * 0.42, h * 0.5, s + 0.02, 0.04), glow('#3A1D1D', 0, 0.0)); win.position.y = y + h * 0.48; g.add(win);
    const lamp = mesh(rbox(s * 0.3, h * 0.36, s + 0.04, 0.03), glow('#FFB347', 0.0, 2.4)); lamp.position.y = y + h * 0.48; g.add(lamp);
    const r = roof(s + 0.95, s + 0.95, 0.55, C.teal); r.position.y = y + h; g.add(r);
    y += h + 0.42;
  }
  const spire = mesh(cyl(0.05, 0.12, 1.4, 10), mat(C.gold, { metalness: 0.6, roughness: 0.3 })); spire.position.y = y + 0.6; g.add(spire);
  for (const k of [0, 1, 2]) { const b = mesh(sph(0.13 - k * 0.025, 10), mat(C.gold, { metalness: 0.6, roughness: 0.3 })); b.position.y = y + 0.25 + k * 0.38; g.add(b); }
  g.userData.top = y + 1.3;
  return g;
}

export function courtyardHouse(w = 2.6, d = 2.0, { wall = C.cream, roofCol = '#3E5A5C' } = {}) {
  const g = new THREE.Group();
  const body = mesh(rbox(w, 1.0, d, 0.06), mat(wall)); body.position.y = 0.5; g.add(body);
  const prism = new THREE.CylinderGeometry(0.75, 0.75, w + 0.3, 3, 1);
  prism.rotateZ(Math.PI / 2);
  const r = mesh(prism, mat(roofCol, { roughness: 0.6 }));
  r.scale.set(1, 0.75, (d + 0.4) / 1.3); r.position.y = 1.32; g.add(r);
  const ridge = mesh(rbox(w + 0.4, 0.1, 0.12, 0.04), mat(C.gold)); ridge.position.y = 1.62; g.add(ridge);
  const door = mesh(rbox(0.38, 0.62, 0.06, 0.03), mat(C.red)); door.position.set(0, 0.32, d / 2 + 0.01); g.add(door);
  for (const s of [-1, 1]) {
    const wnd = mesh(new THREE.CircleGeometry(0.17, 16), glow('#FFC56A', 0.0, 2.0));
    wnd.position.set(s * w * 0.3, 0.55, d / 2 + 0.035); g.add(wnd);
  }
  g.userData.top = 1.7;
  return g;
}

export function gate() {
  const g = new THREE.Group();
  const red = mat(C.red), teal = mat(C.teal), gold = mat(C.gold);
  for (const x of [-1.3, -0.45, 0.45, 1.3]) {
    const p = mesh(cyl(0.11, 0.13, x * x < 0.5 ? 2.5 : 2.0, 12), red);
    p.position.set(x, (x * x < 0.5 ? 2.5 : 2.0) / 2, 0); g.add(p);
  }
  const b1 = mesh(rbox(3.1, 0.22, 0.26, 0.05), teal); b1.position.y = 2.05; g.add(b1);
  const b2 = mesh(rbox(1.4, 0.3, 0.28, 0.05), gold); b2.position.y = 2.32; g.add(b2);
  const r = roof(1.9, 0.6, 0.38, C.teal); r.position.y = 2.5; g.add(r);
  const r2 = roof(1.0, 0.5, 0.3, C.teal); r2.position.set(-1.3, 2.17, 0); g.add(r2);
  const r3 = r2.clone(); r3.position.x = 1.3; g.add(r3);
  g.userData.top = 2.9;
  return g;
}

export function lantern(r = 0.22) {
  const g = new THREE.Group();
  const body = mesh(sph(r, 16), glow(C.red, 0.25, 2.6), { cast: false });
  body.scale.y = 0.82; g.add(body);
  const capM = mat(C.gold, { metalness: 0.5, roughness: 0.35 });
  const c1 = mesh(cyl(r * 0.5, r * 0.5, r * 0.22, 10), capM, { cast: false }); c1.position.y = r * 0.8; g.add(c1);
  const c2 = c1.clone(); c2.position.y = -r * 0.8; g.add(c2);
  const tas = mesh(cyl(0.02, 0.04, r * 0.9, 6), capM, { cast: false }); tas.position.y = -r * 1.3; g.add(tas);
  return g;
}

export function lanternString(p0, p1, n, sag = 0.5) {
  const g = new THREE.Group();
  const cable = mat('#2B2B33');
  const pts = [];
  for (let i = 0; i <= 16; i++) {
    const k = i / 16;
    pts.push([p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k - sag * 4 * k * (1 - k), p0[2] + (p1[2] - p0[2]) * k]);
  }
  for (let i = 0; i < 16; i++) g.add(beam(pts[i], pts[i + 1], 0.02, cable, 5));
  for (let i = 1; i <= n; i++) {
    const k = i / (n + 1);
    const l = lantern(0.2);
    l.position.set(p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k - sag * 4 * k * (1 - k) - 0.3, p0[2] + (p1[2] - p0[2]) * k);
    g.add(l);
  }
  return g;
}

// ------------------------------------------------------------------ quartier créatif
function signPlate(text, w, h, { bg = C.red, fg = '#FFF4E0', font = 'MaShan', night = 2.0 } = {}) {
  const tex = textTexture(text, { font: `200px ${font}`, color: fg, bg, w: 512 * (w / h > 2 ? 2 : 1), h: 256, pad: 6 });
  const m = registerGlow(new THREE.MeshStandardMaterial({ map: tex, emissiveMap: tex, emissive: '#ffffff', emissiveIntensity: 0.15, roughness: 0.5 }), 0.15, night);
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
}
export { signPlate };

export function cinema() {
  const g = new THREE.Group();
  const body = mesh(rbox(3.4, 2.6, 2.8, 0.14), mat('#F3E2C7')); body.position.y = 1.3; g.add(body);
  const top = mesh(rbox(3.5, 0.3, 2.9, 0.1), mat(C.redDeep)); top.position.y = 2.7; g.add(top);
  const marquee = mesh(rbox(3.0, 0.55, 0.3, 0.08), mat(C.red)); marquee.position.set(0, 1.85, 1.5); g.add(marquee);
  for (let i = 0; i < 9; i++) { const b = mesh(sph(0.06, 8), glow(C.goldLight, 0.6, 3.2), { cast: false }); b.position.set(-1.35 + i * 0.34, 2.18, 1.66); g.add(b); }
  const sgn = signPlate('电影院', 2.4, 0.42, { bg: C.red }); sgn.position.set(0, 1.85, 1.66); g.add(sgn);
  const door = mesh(rbox(1.1, 1.0, 0.1, 0.04), glow('#FFD58A', 0.1, 1.8)); door.position.set(0, 0.5, 1.42); g.add(door);
  // bobine de film géante
  const reel = new THREE.Group();
  const disc = mesh(cyl(1.0, 1.0, 0.22, 32), mat('#3D4566', { metalness: 0.4, roughness: 0.35 }));
  disc.rotation.x = Math.PI / 2; reel.add(disc);
  for (let k = 0; k < 5; k++) {
    const a = (k / 5) * Math.PI * 2;
    const hole = mesh(cyl(0.22, 0.22, 0.26, 16), mat('#1B1E2E')); hole.rotation.x = Math.PI / 2; hole.position.set(Math.cos(a) * 0.55, Math.sin(a) * 0.55, 0); reel.add(hole);
  }
  const hub = mesh(cyl(0.16, 0.16, 0.3, 12), mat(C.gold)); hub.rotation.x = Math.PI / 2; reel.add(hub);
  reel.position.set(0.3, 3.95, -0.3); reel.rotation.y = 0.25;
  g.add(reel);
  g.userData.reel = reel;
  g.userData.top = 5.0;
  return g;
}

export function gameStudio() {
  const g = new THREE.Group();
  const body = mesh(rbox(3.0, 3.2, 2.8, 0.14), mat('#3B3F73')); body.position.y = 1.6; g.add(body);
  const stripe = mesh(rbox(3.04, 0.22, 2.84, 0.06), glow(C.neonCyan, 0.25, 2.6)); stripe.position.y = 2.4; g.add(stripe);
  const sgn = signPlate('游戏', 1.5, 0.6, { bg: '#2A2D55', fg: C.neonCyan, night: 2.6 }); sgn.position.set(0, 1.5, 1.42); g.add(sgn);
  // manette géante sur le toit
  const pad = new THREE.Group();
  const bodyM = mat('#F4F1EC', { roughness: 0.4 });
  const b0 = mesh(rbox(1.8, 0.45, 0.95, 0.22), bodyM); pad.add(b0);
  for (const s of [-1, 1]) { const hnd = mesh(rbox(0.6, 0.42, 0.75, 0.21), bodyM); hnd.position.set(s * 0.72, -0.05, 0.42); hnd.rotation.y = s * 0.35; pad.add(hnd); }
  const cols = [C.red, C.gold, C.jade, '#4C7BE0'];
  cols.forEach((c, i) => { const bt = mesh(cyl(0.09, 0.09, 0.12, 12), mat(c)); bt.position.set(0.48 + (i % 2) * 0.2 - 0.1, 0.25, -0.1 + (i < 2 ? -0.1 : 0.12)); pad.add(bt); });
  const dp = mesh(rbox(0.36, 0.1, 0.12, 0.03), mat('#2B2B33')); dp.position.set(-0.5, 0.26, 0); pad.add(dp);
  const dp2 = dp.clone(); dp2.rotation.y = Math.PI / 2; pad.add(dp2);
  pad.position.set(0, 3.7, 0); pad.rotation.x = -0.35;
  g.add(pad);
  // bâton doré du Roi Singe (Voyage vers l'Ouest)
  const staff = beam([-1.1, 3.2, -0.9], [1.0, 5.6, -1.1], 0.07, mat(C.gold, { metalness: 0.7, roughness: 0.25 }), 10);
  g.add(staff);
  for (const p of [[-1.1, 3.2, -0.9], [1.0, 5.6, -1.1]]) { const e = mesh(cyl(0.1, 0.1, 0.3, 10), mat(C.red)); e.position.set(...p); g.add(e); }
  g.userData.pad = pad;
  g.userData.top = 5.0;
  return g;
}

export function toyShop() {
  const g = new THREE.Group();
  const body = mesh(rbox(3.0, 2.2, 2.6, 0.2), mat('#FFC9D4')); body.position.y = 1.1; g.add(body);
  const awn = mesh(rbox(3.1, 0.18, 0.7, 0.06), mat(C.white)); awn.position.set(0, 1.55, 1.5); g.add(awn);
  for (let i = 0; i < 6; i++) { const s = mesh(rbox(0.5, 0.2, 0.72, 0.05), mat(C.red)); s.position.set(-1.25 + i * 0.5, 1.56, 1.5); if (i % 2 === 0) g.add(s); }
  const win = mesh(rbox(2.2, 0.8, 0.08, 0.04), glow('#FFE3A3', 0.1, 1.6)); win.position.set(0, 0.75, 1.3); g.add(win);
  // boîtes surprises « ? » empilées
  const qTex = textTexture('?', { font: '900 italic 200px "Barlow Condensed"', color: '#FFF4E0', bg: C.red, w: 256, h: 256 });
  const qTex2 = textTexture('?', { font: '900 italic 200px "Barlow Condensed"', color: C.red, bg: C.gold, w: 256, h: 256 });
  const boxes = [[-0.6, 0, 0.1, qTex, 0.75], [0.35, 0, -0.2, qTex2, 0.85], [-0.15, 0.82, 0, qTex2, 0.7], [0.75, 0.85, 0.3, qTex, 0.55]];
  const stack = new THREE.Group();
  for (const [x, y, z, tex, s] of boxes) {
    const m = mesh(new THREE.BoxGeometry(s, s, s), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.5 }));
    m.position.set(x, y + s / 2, z); m.rotation.y = x * 0.6; stack.add(m);
  }
  stack.position.y = 2.2; g.add(stack);
  for (const [x, z, c] of [[1.1, -0.8, C.gold], [1.35, -0.4, C.red], [0.95, -0.2, '#7EC8E3']]) {
    const b = mesh(sph(0.26, 14), mat(c, { roughness: 0.3 })); b.scale.y = 1.15; b.position.set(x, 3.9 + z * 0.4, z); g.add(b);
    g.add(beam([x, 2.25, z], [x, 3.65 + z * 0.4, z], 0.012, mat('#555')));
  }
  g.userData.top = 4.3;
  return g;
}

export function liveStudio() {
  const g = new THREE.Group();
  const body = mesh(rbox(2.8, 3.6, 2.6, 0.14), mat('#ECE4DA')); body.position.y = 1.8; g.add(body);
  const scr = textTexture('LIVE ●', { font: '900 italic 150px "Barlow Condensed"', color: '#FFFFFF', bg: '#FF3D6E', w: 512, h: 256 });
  const sm = registerGlow(new THREE.MeshStandardMaterial({ map: scr, emissiveMap: scr, emissive: '#ffffff', emissiveIntensity: 0.55, roughness: 0.4 }), 0.55, 1.8);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(2.1, 1.05), sm);
  screen.position.set(0, 2.6, 1.32); g.add(screen);
  const frame = mesh(rbox(2.3, 1.25, 0.1, 0.05), mat('#2B2B33')); frame.position.set(0, 2.6, 1.27); g.add(frame);
  const ring = mesh(new THREE.TorusGeometry(0.35, 0.06, 10, 28), glow('#FFFFFF', 0.6, 2.4)); ring.position.set(0.9, 4.1, 0); g.add(ring);
  const tri = mesh(cyl(0.03, 0.03, 0.6, 6), mat('#2B2B33')); tri.position.set(0.9, 3.7, 0); g.add(tri);
  const sgn = signPlate('直播', 1.1, 0.5, { bg: '#FF3D6E', fg: '#fff', night: 2.4 }); sgn.position.set(-0.6, 1.2, 1.32); g.add(sgn);
  g.userData.screen = screen;
  g.userData.top = 4.5;
  return g;
}

export function heartGeo() {
  const s = new THREE.Shape();
  s.moveTo(0, -0.35);
  s.bezierCurveTo(-0.05, -0.25, -0.45, -0.05, -0.45, 0.18);
  s.bezierCurveTo(-0.45, 0.42, -0.12, 0.48, 0, 0.26);
  s.bezierCurveTo(0.12, 0.48, 0.45, 0.42, 0.45, 0.18);
  s.bezierCurveTo(0.45, -0.05, 0.05, -0.25, 0, -0.35);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.1, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 2, curveSegments: 10 });
  g.center();
  return g;
}

export function cafe(color = '#F7D8A8') {
  const g = new THREE.Group();
  const body = mesh(rbox(2.0, 1.4, 1.8, 0.12), mat(color)); body.position.y = 0.7; g.add(body);
  const awn = mesh(rbox(2.1, 0.12, 0.6, 0.05), mat(C.jade)); awn.position.set(0, 1.05, 1.1); awn.rotation.x = 0.25; g.add(awn);
  const win = mesh(rbox(1.4, 0.5, 0.06, 0.03), glow('#FFD58A', 0.05, 2.0)); win.position.set(0, 0.6, 0.92); g.add(win);
  const r = mesh(rbox(2.05, 0.18, 1.85, 0.06), mat(C.white)); r.position.y = 1.45; g.add(r);
  g.userData.top = 1.6;
  return g;
}

// ------------------------------------------------------------------ nature
export function karst(r = 1.3, h = 4) {
  const pts = [[0, h], [r * 0.38, h * 0.97], [r * 0.7, h * 0.86], [r * 0.86, h * 0.62], [r * 0.95, h * 0.35], [r, h * 0.08], [r * 0.9, 0]];
  const geo = latheGrad(pts, '#3E8E5B', '#A9D77E', 20);
  const m = mesh(geo, vcol('#ffffff'));
  return m;
}

export function tree(kind = 'round', s = 1) {
  const g = new THREE.Group();
  const trunk = mesh(cyl(0.07, 0.1, 0.6, 8), mat('#8B5E3C')); trunk.position.y = 0.3; g.add(trunk);
  if (kind === 'pine') {
    for (let i = 0; i < 3; i++) { const c = mesh(new THREE.ConeGeometry(0.55 - i * 0.12, 0.7, 10), mat('#3F8F5E')); c.position.y = 0.7 + i * 0.38; g.add(c); }
  } else {
    const col = kind === 'cherry' ? '#F7A8C0' : kind === 'gold' ? '#F2C14E' : '#6DBF5E';
    const c = mesh(sph(0.5, 16), mat(col, { roughness: 0.8 })); c.position.y = 0.95; c.scale.set(1, 1.1, 1); g.add(c);
    const c2 = mesh(sph(0.32, 14), mat(col, { roughness: 0.8 })); c2.position.set(0.28, 0.8, 0.12); g.add(c2);
  }
  g.scale.setScalar(s);
  return g;
}

export function bamboo(n = 8, seed = 1) {
  const g = new THREE.Group();
  let s = seed * 77;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const green = mat('#5DAA4F'), leaf = mat('#7CC36A');
  for (let i = 0; i < n; i++) {
    const x = (rnd() - 0.5) * 1.6, z = (rnd() - 0.5) * 1.6, h = 2.2 + rnd() * 1.6;
    const st = mesh(cyl(0.05, 0.06, h, 8), green); st.position.set(x, h / 2, z); g.add(st);
    const lf = mesh(new THREE.ConeGeometry(0.28, 0.6, 7), leaf); lf.position.set(x, h + 0.1, z); g.add(lf);
  }
  return g;
}

export function cloud(seed = 1) {
  const g = new THREE.Group();
  const m = mat('#FFFFFF', { roughness: 1.0 });
  let s = seed * 131;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  for (let i = 0; i < 6; i++) {
    const r = 0.8 + rnd() * 0.9;
    const b = mesh(sph(r, 16), m, { cast: false, receive: false });
    b.position.set((i - 2.5) * 0.9 + rnd() * 0.4, (rnd() - 0.3) * 0.5 + (i % 2) * 0.3, (rnd() - 0.5) * 0.9);
    b.scale.y = 0.75; g.add(b);
  }
  return g;
}

// ------------------------------------------------------------------ personnages et véhicules
const capsule = new THREE.CapsuleGeometry(0.13, 0.28, 4, 10);
export function person(color = C.red, skin = '#F2C9A8') {
  const g = new THREE.Group();
  const body = mesh(capsule, mat(color)); body.position.y = 0.28; g.add(body);
  const head = mesh(sph(0.12, 12), mat(skin)); head.position.y = 0.62; g.add(head);
  g.userData.body = body;
  return g;
}

export function drone() {
  const g = new THREE.Group();
  const body = mesh(rbox(0.5, 0.14, 0.5, 0.06), mat('#2E3350')); g.add(body);
  for (const [x, z] of [[-0.35, -0.35], [0.35, -0.35], [-0.35, 0.35], [0.35, 0.35]]) {
    const arm = mesh(rbox(0.06, 0.05, 0.06, 0.02), mat('#2E3350')); arm.position.set(x * 0.6, 0, z * 0.6); g.add(arm);
    const rot = mesh(cyl(0.18, 0.18, 0.02, 14), mat('#DDE3EE', { transparent: true, opacity: 0.6 }), { cast: false }); rot.position.set(x, 0.06, z); g.add(rot);
  }
  const l1 = mesh(sph(0.05, 8), glow('#FF3B3B', 1.5, 3), { cast: false }); l1.position.set(0, -0.06, 0.26); g.add(l1);
  const l2 = mesh(sph(0.05, 8), glow('#3BFF8A', 1.5, 3), { cast: false }); l2.position.set(0, -0.06, -0.26); g.add(l2);
  g.userData.lights = [l1, l2];
  return g;
}

export function trainCar(lead = false) {
  const g = new THREE.Group();
  const body = mesh(rbox(1.3, 0.46, 0.44, 0.15), mat(C.white, { roughness: 0.35 })); g.add(body);
  const stripe = mesh(rbox(1.31, 0.08, 0.45, 0.03), mat(C.red)); stripe.position.y = -0.08; g.add(stripe);
  const win = mesh(rbox(1.0, 0.12, 0.452, 0.03), glow('#3C4A66', 0.0, 0.0)); win.position.y = 0.08; g.add(win);
  const winLit = mesh(rbox(0.96, 0.08, 0.455, 0.02), glow('#FFE2A0', 0.0, 2.2)); winLit.position.y = 0.08; g.add(winLit);
  if (lead) {
    const nose = mesh(sph(0.23, 16), mat(C.white, { roughness: 0.35 })); nose.scale.set(1.8, 0.9, 0.95); nose.position.x = 0.62; g.add(nose);
    const ns = mesh(sph(0.235, 16), mat(C.red)); ns.scale.set(1.0, 0.3, 0.96); ns.position.set(0.7, -0.08, 0); g.add(ns);
  }
  return g;
}

export function car(color = '#F6C514') {
  const g = new THREE.Group();
  const body = mesh(rbox(1.5, 0.38, 0.72, 0.14), mat(color, { roughness: 0.3, metalness: 0.15 })); body.position.y = 0.32; g.add(body);
  const cab = mesh(rbox(0.8, 0.3, 0.64, 0.12), mat('#2B3046', { roughness: 0.2, metalness: 0.3 })); cab.position.set(-0.08, 0.6, 0); g.add(cab);
  for (const [x, z] of [[-0.5, 0.36], [0.5, 0.36], [-0.5, -0.36], [0.5, -0.36]]) {
    const w = mesh(cyl(0.16, 0.16, 0.12, 14), mat('#222')); w.rotation.x = Math.PI / 2; w.position.set(x, 0.16, z); g.add(w);
  }
  const hl = mesh(rbox(0.05, 0.08, 0.16, 0.02), glow('#FFF2C0', 0.4, 3.0), { cast: false }); hl.position.set(0.76, 0.36, 0.22); g.add(hl);
  const hl2 = hl.clone(); hl2.position.z = -0.22; g.add(hl2);
  const tl = mesh(rbox(0.04, 0.07, 0.14, 0.02), glow('#FF3030', 0.4, 2.5), { cast: false }); tl.position.set(-0.76, 0.38, 0.24); g.add(tl);
  const tl2 = tl.clone(); tl2.position.z = -0.24; g.add(tl2);
  return g;
}
