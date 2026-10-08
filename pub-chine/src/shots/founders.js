// ACTE 5 — Les fondateurs : une rue chinoise de nuit, néons, et les photos de Nik & Odyo en polaroïds.
import * as THREE from 'three';
import { C, mat, glow, rbox, cyl, sph, mesh, islandBase, windowMat, registerGlow, beam } from '../core/geo.js';
import { seg, clamp, lerp, outBack, outCubic, outQuart, inCubic, outElastic, rng, damped, pulse } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { STREET, AZ } from '../layout.js';
import * as B from './builders.js';

// ordre de récit : duo de nuit, néon + voiture, Gundam, arcade, puis le duo appareil photo à la main
export const PHOTO_ORDER = [1, 2, 3, 4, 0];
export const PHOTO_X = [-11.2, -5.6, 0.0, 5.6, 11.2];

function neonTexture(text, { color = '#FF3D9A', font = '900 italic 150px "Barlow Condensed"', w = 1024, h = 256, tube = 10 } = {}) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineJoin = 'round';
  g.strokeStyle = color; g.lineWidth = tube; g.strokeText(text, w / 2, h / 2 + 6);
  g.strokeStyle = '#FFFFFF'; g.lineWidth = tube * 0.35; g.strokeText(text, w / 2, h / 2 + 6);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

function neonSign(text, w, h, opts = {}) {
  const tex = neonTexture(text, opts);
  const m = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, color: new THREE.Color(1, 1, 1) });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
  plane.userData.mat = m;
  return plane;
}

function shop(w, h, d, { wall, sign, signColor = '#FF3D9A', signFont = '200px MaShan', vertical = null, seed = 1 }) {
  const g = new THREE.Group();
  g.userData.w = w;
  const body = mesh(rbox(w, h, d, 0.12), windowMat(Math.round(w * 1.6), Math.round(h * 1.2), { frame: wall, pane: '#3B4466', lit: '#FFC978', seed, litRatio: 0.42, night: 0.75 }));
  body.position.y = h / 2; g.add(body);
  const ground = mesh(rbox(w * 0.96, 1.5, 0.12, 0.04), glow('#FFD9A0', 0.2, 1.1)); ground.position.set(0, 0.8, d / 2 + 0.02); g.add(ground);
  const awn = mesh(rbox(w * 0.98, 0.14, 0.9, 0.05), mat(C.red)); awn.position.set(0, 1.75, d / 2 + 0.4); awn.rotation.x = 0.18; g.add(awn);
  const roof = mesh(rbox(w * 1.02, 0.25, d * 1.02, 0.08), mat('#4A4F68')); roof.position.y = h + 0.1; g.add(roof);
  for (let k = 0; k < 2; k++) { const ac = mesh(rbox(0.6, 0.4, 0.3, 0.05), mat('#C9CDD8')); ac.position.set(-w / 2 + 0.8 + k * 1.6, h * 0.55 + k * 0.9, d / 2 + 0.15); g.add(ac); }
  if (sign) {
    const s = neonSign(sign, w * 0.8, w * 0.2, { color: signColor, font: signFont, tube: 14 });
    s.position.set(0, 2.35, d / 2 + 0.09); g.add(s); g.userData.sign = s;
  }
  if (vertical) {
    const vs = new THREE.Group();
    const board = mesh(rbox(0.16, 2.8, 0.9, 0.04), mat('#2A2E44')); vs.add(board);
    const cv = document.createElement('canvas'); cv.width = 128; cv.height = 512;
    const cg = cv.getContext('2d'); cg.font = '110px MaShan'; cg.textAlign = 'center'; cg.fillStyle = vertical.color;
    [...vertical.text].forEach((ch, i) => cg.fillText(ch, 64, 120 + i * 120));
    const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 2.6), registerGlow(new THREE.MeshStandardMaterial({ map: tx, emissiveMap: tx, emissive: '#ffffff', emissiveIntensity: 0.3, transparent: true }), 0.3, 2.6));
    face.rotation.y = Math.PI / 2; face.position.x = 0.09; vs.add(face);
    const face2 = face.clone(); face2.rotation.y = -Math.PI / 2; face2.position.x = -0.09; vs.add(face2);
    vs.position.set(w / 2 - 0.3, h * 0.62, d / 2 + 0.55);
    g.add(vs);
  }
  return g;
}

function polaroid(tex) {
  const g = new THREE.Group();
  const frame = mesh(rbox(3.1, 3.5, 0.08, 0.04), new THREE.MeshStandardMaterial({ color: '#FFFDF8', roughness: 0.6, emissive: '#FFF6E8', emissiveIntensity: 0.32 }));
  g.add(frame);
  const photo = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 2.1), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.55, emissive: '#ffffff', emissiveMap: tex, emissiveIntensity: 0.55 }));
  photo.position.set(0, 0.32, 0.045);
  g.add(photo);
  const tape = mesh(rbox(0.9, 0.3, 0.02, 0.01), mat('#F2D27A', { transparent: true, opacity: 0.85 }), { cast: false });
  tape.position.set(0, 1.72, 0.06); tape.rotation.z = 0.08; g.add(tape);
  g.userData.photo = photo;
  return g;
}

export function build(ctx) {
  const { scene, T, overlay, photos } = ctx;
  const R = rng(64);
  const root = new THREE.Group();
  root.position.set(...STREET);
  scene.add(root);

  root.add(islandBase(28, 15, { top: '#4A4F68', layers: [C.earth, C.earthDark, C.rock] }));
  const road = mesh(rbox(28, 0.06, 4.0, 0.02), mat(C.asphaltNight, { roughness: 0.75 })); road.position.set(0, 0.03, 0.6); root.add(road);
  for (let x = -12; x <= 12; x += 2.4) { const l = mesh(rbox(1.2, 0.07, 0.12, 0.02), glow('#F2E7C9', 0.1, 0.6), { cast: false }); l.position.set(x, 0.05, 0.6); root.add(l); }
  for (const z of [-2.2, 3.4]) { const sw = mesh(rbox(28, 0.22, 1.6, 0.05), mat('#8E8FA3')); sw.position.set(0, 0.11, z); root.add(sw); }
  const front = mesh(rbox(28, 0.12, 3.2, 0.05), mat('#5C6178')); front.position.set(0, 0.06, 5.8); root.add(front);

  // façades
  const shops = [
    shop(5.0, 6.5, 3.4, { wall: '#C9B7A4', sign: '创意工坊', signColor: '#FF3D9A', vertical: { text: '创作', color: '#29F0E4' }, seed: 11 }),
    shop(4.4, 5.2, 3.4, { wall: '#9FB4C6', sign: '茶馆', signColor: '#FFB23A', seed: 12 }),
    shop(5.4, 8.0, 3.4, { wall: '#B8A8C9', sign: null, vertical: { text: '梦想', color: '#FF3D9A' }, seed: 13 }),
    shop(4.4, 5.8, 3.4, { wall: '#C7B6A0', sign: '夜宵', signColor: '#29F0E4', seed: 14 }),
    shop(5.0, 6.8, 3.4, { wall: '#A9BFB4', sign: '潮流', signColor: '#FFE45C', vertical: { text: '直播', color: '#FFB23A' }, seed: 15 }),
  ];
  let x = -12.3;
  shops.forEach((s) => {
    const w = s.userData.w;
    s.position.set(x + w / 2, 0.2, -4.9);
    root.add(s);
    x += w + 0.35;
  });
  // grand néon sur le toit du bâtiment central : NIK & ODYO
  const bigNeon = neonSign('NIK & ODYO', 9.5, 2.4, { color: '#FF3D9A', tube: 16, font: '900 italic 170px "Barlow Condensed"' });
  const neonFrame = mesh(rbox(10.2, 2.9, 0.2, 0.08), mat('#20243A'));
  const neonGroup = new THREE.Group();
  neonGroup.add(neonFrame); bigNeon.position.z = 0.12; neonGroup.add(bigNeon);
  for (const sx of [-3.5, 3.5]) neonGroup.add(beam([sx, -1.45, -0.2], [sx, -2.6, -0.2], 0.08, mat('#3A3F55')));
  neonGroup.position.set(shops[2].position.x, 8.2 + 2.6 + 0.2, -4.9);
  root.add(neonGroup);

  // lanternes au-dessus de la rue
  for (const [x0, x1] of [[-11, -3], [-1.5, 6], [7, 12.5]]) {
    const ls = B.lanternString([x0, 4.2, -3.2], [x1, 4.2, 4.2], 5, 0.5);
    root.add(ls);
  }
  for (const xx of [-11.5, -3.2, 5.6, 12.2]) {
    const pole = mesh(cyl(0.07, 0.09, 4.2, 8), mat('#3A3F55')); pole.position.set(xx, 2.1, 4.25); root.add(pole);
    const lamp = mesh(sph(0.22, 12), glow('#FFE2A8', 0.2, 3.0), { cast: false }); lamp.position.set(xx, 4.25, 4.25); root.add(lamp);
  }
  // voitures : la jaune (clin d'œil à la photo) garée, un taxi rouge qui passe
  const yellow = B.car('#F6C514'); yellow.position.set(2.2, 0.06, -0.8); root.add(yellow);
  const taxi = B.car('#D8262E'); root.add(taxi);
  const roofSign = mesh(rbox(0.3, 0.12, 0.2, 0.03), glow('#FFFFFF', 0.5, 2.5)); roofSign.position.set(-0.1, 0.8, 0); taxi.add(roofSign);
  // passants
  const walkers = [];
  for (let i = 0; i < 9; i++) {
    const p = B.person([C.red, C.gold, C.white, '#4C7BE0', C.jade, '#9B6BD6'][i % 6]);
    p.scale.setScalar(1.6);
    p.userData.x0 = -12 + R() * 24; p.userData.z = R() > 0.5 ? -2.2 : 3.4; p.userData.v = (R() > 0.5 ? 1 : -1) * (0.5 + R() * 0.5); p.userData.ph = R() * 6;
    root.add(p); walkers.push(p);
  }

  // polaroïds
  const pols = PHOTO_ORDER.map((pi, k) => {
    const p = polaroid(photos[pi]);
    p.position.set(PHOTO_X[k], 4.9 + (k % 2 ? 0.4 : -0.2), 3.2);
    p.userData.k = k;
    root.add(p);
    return p;
  });
  ctx.founders = { root, pols, neonGroup };

  // ---------------------------------------------------------------- typographie
  const title = overlay.add('fTitle', `<div class="display white" style="font-size:170px;text-shadow:0 0 28px rgba(255,61,154,0.85),0 0 6px rgba(255,255,255,0.6)">${Overlay.letters('NIK & ODYO', 'ch f')}</div>
     <div class="cond" style="font-size:30px;letter-spacing:0.32em;color:#29F0E4;margin-top:12px;text-shadow:0 2px 10px rgba(5,6,20,0.95),0 0 3px rgba(5,6,20,0.9)"><span class="fs">FONDATEURS · CREATOR IS THE NEW ATHLETE</span></div>`);
  const l1 = overlay.add('fL1', `<div class="body white" style="font-size:40px;font-weight:600;padding:10px 22px;border-radius:14px;background:rgba(8,10,30,0.72)">Créateurs, entrepreneurs, sur le terrain en Chine.</div>`);
  const l2 = overlay.add('fL2', `<div class="display white" style="font-size:84px;text-shadow:0 4px 18px rgba(5,6,20,0.9)">Ils ont tracé la voie. <span style="color:#FF3D9A">À toi de courir.</span></div>`);

  const F = T.founders;
  function update(t) {
    root.visible = t > F.night[0] - 0.6;
    // néon : allumage avec scintillement
    const n0 = F.neon;
    const fl = t < n0 ? 0 : t < n0 + 0.6 ? (Math.sin(t * 90) > 0.2 ? 1 : 0.15) * (Math.sin(t * 37) > -0.5 ? 1 : 0.3) : 1;
    bigNeon.userData.mat.color.setScalar(2.6 * fl + 0.05);
    shops.forEach((s, i) => { if (s.userData.sign) s.userData.sign.userData.mat.color.setScalar((t > n0 - 0.3 + i * 0.12 ? 2.2 : 0.2) * (0.92 + 0.08 * Math.sin(t * 13 + i))); });
    // taxi
    const tx = ((t * 3.2) % 34) - 17;
    taxi.position.set(tx, 0.06, 1.6); taxi.rotation.y = 0;
    walkers.forEach((w) => {
      let xx = w.userData.x0 + w.userData.v * t;
      xx = ((xx + 13) % 26 + 26) % 26 - 13;
      w.position.set(xx, 0.22, w.userData.z);
      w.rotation.y = w.userData.v > 0 ? 0 : Math.PI;
      w.userData.body.position.y = 0.28 + Math.abs(Math.sin(t * 8 + w.userData.ph)) * 0.03;
    });
    // polaroïds : chacun arrive en tournoyant, flash, puis flotte
    pols.forEach((p) => {
      const k = p.userData.k;
      const a = F.photos[k];
      const pr = clamp((t - a) / 0.7);
      p.visible = t > a;
      const e = outBack(pr, 1.5);
      p.scale.setScalar(Math.max(0.001, e * 1.75));
      p.rotation.set(0, AZ + (1 - outCubic(pr)) * Math.PI * 1.5, (k % 2 ? -0.07 : 0.06) + 0.02 * Math.sin(t * 1.3 + k));
      p.position.y = 4.9 + (k % 2 ? 0.4 : -0.2) + 0.12 * Math.sin(t * 1.6 + k * 1.3);
      p.userData.photo.material.emissiveIntensity = 0.88 + 1.0 * Math.exp(-Math.max(0, t - a - 0.45) / 0.18) * (t > a + 0.45 ? 1 : 0);
    });
  }

  function overlayFn(t) {
    const a = F.neon + 0.3, b = F.end - 0.2;
    const on = t > a - 0.02 && t < b;
    const out = inCubic(seg(t, b - 0.35, b));
    style(title, { x: 1800 - title.offsetWidth, y: 90, o: on ? 1 - out : 0, blur: out * 8 });
    title.style.textAlign = 'right';
    title.querySelectorAll('.f').forEach((c, i) => {
      const p = outBack(seg(t, a + i * 0.04, a + 0.5 + i * 0.04), 2.2);
      const flick = t < a + 0.8 + i * 0.04 && Math.sin(t * 70 + i * 3) < -0.6 ? 0.35 : 1;
      c.style.opacity = String(clamp(p) * flick);
      c.style.transform = `scale(${0.6 + 0.4 * p})`;
    });
    const fs = title.querySelector('.fs');
    const k = outCubic(seg(t, a + 0.7, a + 1.2));
    fs.style.display = 'inline-block'; fs.style.opacity = String(k); fs.style.transform = `translateX(${(1 - k) * -30}px)`;
    const c1 = 49.6, d1 = 52.3;
    const p1 = outQuart(seg(t, c1, c1 + 0.5)), o1 = inCubic(seg(t, d1 - 0.3, d1));
    style(l1, { x: 1800 - l1.offsetWidth, y: 372 + (1 - p1) * 30, o: t > c1 && t < d1 ? p1 * (1 - o1) : 0 });
    const c2 = 52.5, d2 = F.end - 0.2;
    const p2 = outQuart(seg(t, c2, c2 + 0.55)), o2 = inCubic(seg(t, d2 - 0.35, d2));
    style(l2, { x: 124, y: 900 + (1 - p2) * 40, o: t > c2 && t < d2 ? p2 * (1 - o2) : 0 });
  }

  return { update, overlay: overlayFn };
}
