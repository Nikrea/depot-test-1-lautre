// ACTE 3 — La marque : un stade, un créateur qui court, et CREATOR IS THE NEW ATHLETE qui s'écrase en 3D.
import * as THREE from 'three';
import { C, mat, glow, rbox, cyl, sph, mesh, islandBase, registerGlow } from '../core/geo.js';
import { seg, clamp, outBack, outCubic, outQuart, inCubic, inQuad, damped, rng, pulse } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { letterGeos } from '../core/text3d.js';
import { STADIUM, AZ } from '../layout.js';

// piste : deux lignes droites + deux virages
const LS = 10, RR = 3.6, LANE = 1.0;
function ovalShape(r, shape = new THREE.Shape(), hole = false) {
  const h = LS / 2;
  const s = hole ? new THREE.Path() : shape;
  s.moveTo(-h, -r);
  s.lineTo(h, -r);
  s.absarc(h, 0, r, -Math.PI / 2, Math.PI / 2, false);
  s.lineTo(-h, r);
  s.absarc(-h, 0, r, Math.PI / 2, 1.5 * Math.PI, false);
  return s;
}
function trackPoint(s, r) {
  const h = LS / 2, arc = Math.PI * r, per = 2 * LS + 2 * arc;
  s = ((s % per) + per) % per;
  if (s < LS) return { x: -h + s, z: r, h: 0 };
  s -= LS;
  if (s < arc) { const a = Math.PI / 2 - s / r; return { x: h + Math.cos(a) * r, z: Math.sin(a) * r, h: Math.PI / 2 - a }; }
  s -= arc;
  if (s < LS) return { x: h - s, z: -r, h: Math.PI };
  s -= LS;
  const a = -Math.PI / 2 - s / r;
  return { x: -h + Math.cos(a) * r, z: Math.sin(a) * r, h: Math.PI / 2 - a };
}

function runner() {
  const g = new THREE.Group();
  const skin = mat('#E8B48F'), shirt = mat(C.red), shorts = mat(C.ink), shoe = mat(C.white), capM = mat(C.ink);
  const limb = (r, len, m) => { const p = new THREE.Group(); const c = mesh(new THREE.CapsuleGeometry(r, len, 4, 10), m); c.position.y = -len / 2 - r * 0.2; p.add(c); return p; };
  const hips = new THREE.Group(); hips.position.y = 1.0; g.add(hips);
  const torso = mesh(new THREE.CapsuleGeometry(0.2, 0.45, 4, 12), shirt); torso.position.y = 0.38; hips.add(torso);
  const head = mesh(sph(0.17, 16), skin); head.position.y = 0.92; hips.add(head);
  const cap = mesh(new THREE.SphereGeometry(0.18, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), capM); cap.position.y = 0.95; hips.add(cap);
  const brim = mesh(rbox(0.2, 0.03, 0.2, 0.01), capM); brim.position.set(0.17, 0.96, 0); hips.add(brim);
  const parts = {};
  for (const side of [-1, 1]) {
    const th = limb(0.08, 0.36, shorts); th.position.set(0, 0, side * 0.12); hips.add(th);
    const sh = limb(0.065, 0.36, skin); sh.position.y = -0.5; th.add(sh);
    const ft = mesh(rbox(0.22, 0.08, 0.11, 0.03), shoe); ft.position.set(0.05, -0.5, 0); sh.add(ft);
    const ua = limb(0.06, 0.26, shirt); ua.position.set(0, 0.62, side * 0.25); hips.add(ua);
    const fa = limb(0.05, 0.24, skin); fa.position.y = -0.36; ua.add(fa);
    parts[side] = { th, sh, ua, fa };
  }
  const phone = mesh(rbox(0.16, 0.1, 0.06, 0.02), mat('#2B2B33')); phone.position.set(0.04, -0.34, 0); parts[1].fa.add(phone);
  const lens = mesh(cyl(0.03, 0.03, 0.03, 10), glow('#FF4040', 1.2, 2.5), { cast: false }); lens.rotation.z = Math.PI / 2; lens.position.set(0.09, 0, 0); phone.add(lens);
  g.userData = { hips, torso, parts };
  g.scale.setScalar(1.6);
  return g;
}

function pose(r, t, speed = 2.5) {
  const { hips, torso, parts } = r.userData;
  const ph = t * Math.PI * 2 * speed * 0.5;
  hips.position.y = 1.0 + Math.abs(Math.sin(ph)) * 0.08;
  torso.rotation.z = -0.22;
  for (const side of [-1, 1]) {
    const s = Math.sin(ph + (side > 0 ? 0 : Math.PI));
    const p = parts[side];
    p.th.rotation.z = 0.75 * s;
    p.sh.rotation.z = -0.9 * Math.max(0, -Math.sin(ph + (side > 0 ? 0 : Math.PI) + 0.6)) - 0.15;
    p.ua.rotation.z = -0.7 * s;
    p.fa.rotation.z = 1.1 + 0.2 * s;
  }
}

export function build(ctx) {
  const { scene, T, overlay, fonts } = ctx;
  const R = rng(21);
  const root = new THREE.Group();
  root.position.set(...STADIUM);
  scene.add(root);

  // île + terrain
  const base = islandBase(30, 26, { top: '#7CC163' });
  root.add(base);
  const grassTex = (() => {
    const c = document.createElement('canvas'); c.width = 512; c.height = 64;
    const g = c.getContext('2d');
    for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? '#78BF5E' : '#86C96B'; g.fillRect(i * 64, 0, 64, 64); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const field = new THREE.Mesh(new THREE.ShapeGeometry(ovalShape(RR - 0.05), 48), new THREE.MeshStandardMaterial({ map: grassTex, roughness: 0.9 }));
  field.rotation.x = -Math.PI / 2; field.position.y = 0.02; field.receiveShadow = true;
  // UV du terrain : bandes de tonte
  { const pos = field.geometry.attributes.position, uv = field.geometry.attributes.uv;
    for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + LS / 2 + RR) / (LS + 2 * RR), 0.5); uv.needsUpdate = true; }
  root.add(field);
  const trackShape = ovalShape(RR + LANE * 4);
  trackShape.holes.push(ovalShape(RR, undefined, true));
  const track = mesh(new THREE.ExtrudeGeometry(trackShape, { depth: 0.12, bevelEnabled: false, curveSegments: 40 }), mat('#C9483E', { roughness: 0.85 }));
  track.rotation.x = -Math.PI / 2; track.position.y = 0.0; root.add(track);
  for (let k = 1; k < 4; k++) {
    const sh = ovalShape(RR + LANE * k + 0.035);
    sh.holes.push(ovalShape(RR + LANE * k - 0.035, undefined, true));
    const line = mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.125, bevelEnabled: false, curveSegments: 40 }), mat('#FFF6EC'), { cast: false });
    line.rotation.x = -Math.PI / 2; root.add(line);
  }
  const finish = mesh(rbox(0.25, 0.13, LANE * 4, 0.02), mat('#FFF6EC'), { cast: false }); finish.position.set(2, 0.01, RR + LANE * 2); root.add(finish);

  // tribunes + public
  const stands = new THREE.Group(); root.add(stands);
  const seatCols = [C.red, '#F2F2F2', C.gold];
  const crowd = [];
  for (let k = 0; k < 4; k++) {
    const step = mesh(rbox(22, 0.5 + k * 0.55, 0.95, 0.06), mat(k % 2 ? '#E9E1D6' : '#DDD3C6'));
    step.position.set(0, (0.5 + k * 0.55) / 2, -(RR + LANE * 4 + 0.9 + k * 0.95));
    stands.add(step);
    for (let i = 0; i < 28; i++) {
      const p = mesh(new THREE.CapsuleGeometry(0.13, 0.16, 3, 8), mat(seatCols[(i + k) % 3]));
      p.position.set(-10.3 + i * 0.76 + (R() - 0.5) * 0.2, 0.5 + k * 0.55 + 0.25, -(RR + LANE * 4 + 0.9 + k * 0.95));
      p.userData.ph = R() * 6; p.userData.y = p.position.y;
      stands.add(p); crowd.push(p);
    }
  }
  const roofM = mat(C.white);
  const roof = mesh(rbox(23, 0.25, 4.6, 0.1), roofM); roof.position.set(0, 3.9, -(RR + LANE * 4 + 2.4)); stands.add(roof);
  for (const x of [-11, -3.7, 3.7, 11]) { const p = mesh(cyl(0.12, 0.12, 3.9, 8), roofM); p.position.set(x, 1.95, -(RR + LANE * 4 + 4.4)); stands.add(p); }
  // projecteurs
  const lights = [];
  for (const [x, z] of [[-13.6, -9.5], [13.6, -9.5], [-13.6, 9.5], [13.6, 9.5]]) {
    const pole = mesh(cyl(0.12, 0.16, 6.5, 8), mat('#C9CDD8')); pole.position.set(x, 3.25, z); root.add(pole);
    const pan = mesh(rbox(1.4, 0.9, 0.25, 0.06), mat('#3A3F55')); pan.position.set(x, 6.6, z); pan.lookAt(0, 0, 0); root.add(pan);
    const lit = mesh(rbox(1.2, 0.7, 0.05, 0.03), glow('#FFF6D8', 0.6, 3.0), { cast: false }); lit.position.set(0, 0, 0.14); pan.add(lit);
    lights.push(pan);
  }
  // arbres décoratifs aux coins
  for (const [x, z] of [[-14, 3.5], [14, 2.5], [-13.8, -4.5], [13.9, -5]]) {
    const tr = new THREE.Group();
    const tk = mesh(cyl(0.08, 0.1, 0.6, 8), mat('#8B5E3C')); tk.position.y = 0.3; tr.add(tk);
    const cn = mesh(sph(0.55, 14), mat('#5FB45A')); cn.position.y = 1.0; tr.add(cn);
    tr.position.set(x, 0, z); root.add(tr);
  }

  // le coureur-créateur
  const run = runner();
  root.add(run);

  // ---------------------------------------------------------------- titre 3D
  const title = new THREE.Group();
  title.position.set(0, 0.1, 0.4);
  title.rotation.y = AZ;
  root.add(title);
  const frontW = registerGlow(new THREE.MeshStandardMaterial({ color: '#FFF9F0', roughness: 0.35, emissive: '#FFF6EA', emissiveIntensity: 0.42 }), 0.42, 0.55);
  const frontG = registerGlow(new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.4, emissive: C.ink, emissiveIntensity: 0 }), 0, 0.2);
  const sideGold = new THREE.MeshStandardMaterial({ color: C.gold, roughness: 0.3, metalness: 0.4 });
  const sideR = new THREE.MeshStandardMaterial({ color: C.red, roughness: 0.5 });
  const LINES = [
    { text: 'CREATOR', size: 2.5, y: 5.9, front: frontW, side: sideR, t0: T.brand.slam },
    { text: 'IS THE NEW', size: 1.3, y: 3.75, front: frontG, side: sideGold, t0: T.brand.slam + 0.42 },
    { text: 'ATHLETE', size: 2.5, y: 0.0, front: frontW, side: sideR, t0: T.brand.slam + 0.7 },
  ];
  const letters = [];
  for (const L of LINES) {
    const { letters: ls, width } = letterGeos(fonts.title, L.text, { size: L.size, depth: L.size * 0.32, bevel: L.size * 0.025 });
    ls.forEach((l, i) => {
      const m = new THREE.Mesh(l.geo, [L.front, L.side]);
      m.castShadow = true; m.receiveShadow = true;
      const piv = new THREE.Group();
      const bb = l.geo.boundingBox;
      const cx = (bb.min.x + bb.max.x) / 2;
      m.position.set(-cx, 0, -L.size * 0.16);
      piv.add(m);
      piv.position.set(l.x + cx - width / 2, L.y, 0);
      piv.userData = { y: L.y, t: L.t0 + i * 0.035, size: L.size };
      title.add(piv);
      letters.push(piv);
    });
  }
  // poussière à l'impact
  const dust = [];
  const dustM = mat('#F3E3CC', { transparent: true, opacity: 0.85 });
  for (let i = 0; i < 26; i++) { const d = mesh(sph(0.35, 10), dustM, { cast: false, receive: false }); d.userData.a = (i / 26) * Math.PI * 2; title.add(d); dust.push(d); }

  ctx.brand = { title, letters, root };

  // ---------------------------------------------------------------- typographie
  const pre = overlay.add('brandPre', Overlay.words('LE TALENT NE SUFFIT PLUS.'), 'display ink');
  pre.style.fontSize = '120px';
  const sub = overlay.add('brandSub', `<div style="text-align:center">
      <div class="pill" style="display:inline-block;background:#1B1E2E;color:#FBF7F2">La formation de Nik &amp; Odyo</div>
      <div class="body ink" style="display:inline-block;font-size:38px;font-weight:600;margin-top:14px;padding:10px 26px;border-radius:16px;background:rgba(255,250,242,0.9)">Pour vivre de sa passion. Pour de vrai.</div></div>`);

  const slam = T.brand.slam;
  function update(t) {
    root.visible = (t > 21.5 && t < 29.5) || t > T.finale.pull[0] - 0.5;
    // coureur : tour de piste continu
    const sRun = 7.2 * (t - 21.0);
    const p = trackPoint(sRun, RR + LANE * 1.5);
    run.position.set(p.x, 0.12, p.z);
    run.rotation.y = p.h;
    pose(run, t, 2.6);

    // lettres
    for (const piv of letters) {
      const { t: lt, y } = piv.userData;
      const k = seg(t, lt - 0.38, lt);
      piv.visible = t > lt - 0.38;
      const fall = 1 - inQuad(k);
      piv.position.y = y + fall * 16;
      const tau = t - lt;
      const sq = tau > 0 ? 0.28 * Math.exp(-tau / 0.09) * Math.cos(2 * Math.PI * 4 * tau) : 0;
      piv.scale.set(1 + sq * 0.6, 1 - sq, 1 + sq * 0.6);
      piv.rotation.z = tau < 0 ? (1 - k) * 0.5 * Math.sin(piv.position.x) : 0;
    }
    // poussière
    dust.forEach((d, i) => {
      const tau = t - (slam + 0.7);
      const on = tau > 0 && tau < 1.2;
      d.visible = on;
      if (!on) return;
      const r = 1 + outCubic(clamp(tau / 1.0)) * 6.5;
      d.position.set(Math.cos(d.userData.a) * r, 0.3 + tau * 0.6, Math.sin(d.userData.a) * r * 0.5);
      d.scale.setScalar(Math.max(0.001, (1 - tau / 1.2) * (0.8 + (i % 3) * 0.3)));
    });
    // le public saute à chaque impact
    const jump = pulse(t - slam, 0.02, 0.35) + pulse(t - slam - 0.42, 0.02, 0.3) + pulse(t - slam - 0.7, 0.02, 0.5);
    crowd.forEach((c) => { c.position.y = c.userData.y + Math.max(0, Math.sin(t * 9 + c.userData.ph)) * 0.18 * clamp(jump * 1.5) + 0.04 * Math.sin(t * 3 + c.userData.ph); });
  }

  function camera(t, s) {
    const sh = damped(t - slam, 9, 7) * 0.035 + damped(t - slam - 0.42, 10, 8) * 0.02 + damped(t - slam - 0.7, 8, 6) * 0.04;
    s.shake[0] += sh * 0.6;
    s.shake[1] += sh;
  }

  function post(t, { fin }) {
    fin.uniforms.uFlash.value = Math.max(fin.uniforms.uFlash.value, 0.55 * Math.exp(-Math.max(0, t - slam) / 0.12) * (t >= slam ? 1 : 0));
  }

  function overlayFn(t) {
    const [a, b] = T.brand.pre;
    const ws = pre.querySelectorAll('.wi');
    style(pre, { x: 960 - pre.offsetWidth / 2, y: 110, o: t > a - 0.05 && t < b + 0.05 ? 1 : 0 });
    ws.forEach((w, i) => {
      const p = outQuart(seg(t, a + i * 0.07, a + i * 0.07 + 0.4));
      const o = inCubic(seg(t, b - 0.18, b));
      w.style.transform = `translateY(${(1 - p) * 110 - o * 110}%)`;
    });
    const [c, d] = T.brand.sub;
    const pin = outBack(seg(t, c, c + 0.6), 1.5), pout = inCubic(seg(t, d - 0.35, d));
    style(sub, { x: 960 - 520, y: 900 + (1 - pin) * 40, o: t > c && t < d ? clamp(pin) * (1 - pout) : 0 });
    sub.style.width = '1040px';
  }

  return { update, camera, post, overlay: overlayFn };
}
