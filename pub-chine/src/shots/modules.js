// ACTE 4 — Le programme : 7 îles-stations, une mesure (2 s) chacune, puis la médaille du créateur complet.
import * as THREE from 'three';
import { C, mat, glow, rbox, cyl, sph, mesh, islandBase, beam, registerGlow } from '../core/geo.js';
import { seg, clamp, lerp, outBack, outCubic, outQuart, inCubic, outElastic, outBounce, inOutCubic, damped, rng, pulse } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { MODULES, MEDAL, AZ } from '../layout.js';
import { textMesh } from '../core/text3d.js';
import * as B from './builders.js';

export const MOD = [
  { n: '01', title: 'Créer son projet', line: "Transformer une idée en projet concret.", accent: C.red },
  { n: '02', title: 'Trouver son axe', line: "Concentrer son énergie là où sont ses objectifs.", accent: C.gold },
  { n: '03', title: "S'exprimer", line: 'Trouver sa voix. Captiver. Convaincre.', accent: '#4C7BE0' },
  { n: '04', title: 'Négocier', line: 'Défendre sa valeur, signer les bons deals.', accent: C.jade },
  { n: '05', title: 'Gérer son business', line: 'Piloter une activité créative rentable.', accent: '#F07F4F' },
  { n: '06', title: 'Tenir dans le temps', line: "Discipline, énergie, régularité : l'endurance.", accent: '#5DAA4F' },
  { n: '07', title: "S'entourer", line: 'Bâtir son équipe et son réseau créatif.', accent: '#9B6BD6' },
];

// ------------------------------------------------------------------ 01 : blocs qui s'assemblent + idée
function mBlocks() {
  const g = new THREE.Group();
  const parts = [
    [rbox(3.2, 0.6, 2.2, 0.12), C.red, [0, 0.3, 0]],
    [rbox(0.8, 1.6, 2.0, 0.12), C.gold, [-1.1, 1.4, 0]],
    [rbox(0.8, 1.6, 2.0, 0.12), C.gold, [1.1, 1.4, 0]],
    [rbox(1.2, 0.9, 0.5, 0.1), '#4C7BE0', [0, 0.95, 0.75]],
    [rbox(3.4, 0.5, 2.4, 0.12), C.jade, [0, 2.45, 0]],
    [rbox(1.4, 0.6, 1.4, 0.12), C.white, [0, 3.0, 0]],
  ];
  const blocks = parts.map(([geo, col, p], i) => { const m = mesh(geo, mat(col, { roughness: 0.45 })); m.userData.p = p; m.userData.i = i; g.add(m); return m; });
  const bulb = new THREE.Group();
  const glass = mesh(sph(0.55, 20), glow('#FFE38A', 0.4, 2.5, { roughness: 0.2 }), { cast: false }); glass.position.y = 0.55; bulb.add(glass);
  const sock = mesh(cyl(0.25, 0.22, 0.35, 14), mat('#9AA0B4', { metalness: 0.6, roughness: 0.3 })); sock.position.y = 0.0; bulb.add(sock);
  bulb.position.y = 3.35;
  g.add(bulb);
  const rays = [];
  for (let k = 0; k < 8; k++) { const r = mesh(rbox(0.08, 0.5, 0.08, 0.03), glow('#FFD24A', 1.0, 2.5), { cast: false }); r.userData.a = (k / 8) * Math.PI * 2; bulb.add(r); rays.push(r); }
  g.userData.anim = (tau) => {
    blocks.forEach((b) => {
      const t0 = b.userData.i * 0.11;
      const p = clamp((tau - t0) / 0.32);
      const [x, y, z] = b.userData.p;
      b.visible = tau > t0;
      b.position.set(x, y + (1 - outBounce(p)) * 5, z);
    });
    const pb = outElastic(clamp((tau - 0.85) / 0.6), 0.4);
    bulb.visible = tau > 0.85;
    bulb.scale.setScalar(Math.max(pb, 0.001));
    glass.material.emissiveIntensity = 0.4 + 2.2 * clamp((tau - 0.95) / 0.2);
    rays.forEach((r) => { const k = outCubic(clamp((tau - 1.0) / 0.35)); r.visible = tau > 1.0; r.position.set(Math.cos(r.userData.a) * (0.8 + k * 0.5), 0.55 + Math.sin(r.userData.a) * (0.8 + k * 0.5), 0); r.rotation.z = r.userData.a - Math.PI / 2; r.scale.y = Math.max(0.01, k); });
    bulb.rotation.y = AZ;
  };
  return g;
}

// ------------------------------------------------------------------ 02 : cible + flèche
function mTarget() {
  const g = new THREE.Group();
  const tgt = new THREE.Group();
  const cols = [C.white, C.red, C.white, C.red, C.gold];
  cols.forEach((c, i) => { const d = mesh(cyl(1.7 - i * 0.34, 1.7 - i * 0.34, 0.25 + i * 0.03, 40), mat(c, { roughness: 0.5 })); d.rotation.x = Math.PI / 2; d.position.z = i * 0.015; tgt.add(d); });
  const legM = mat('#8B5E3C');
  for (const s of [-1, 1]) { const l = beam([s * 0.9, -2.2, -0.6], [s * 0.4, 0.4, -0.15], 0.07, legM); tgt.add(l); }
  tgt.position.y = 2.3;
  g.add(tgt);
  const arrow = new THREE.Group();
  const shaft = mesh(cyl(0.05, 0.05, 2.4, 8), mat('#5A3E2B')); shaft.rotation.z = Math.PI / 2; arrow.add(shaft);
  const head = mesh(new THREE.ConeGeometry(0.14, 0.4, 10), mat('#C9CDD8', { metalness: 0.6, roughness: 0.3 })); head.rotation.z = -Math.PI / 2; head.position.x = 1.3; arrow.add(head);
  for (const s of [-1, 1]) { const f = mesh(rbox(0.45, 0.02, 0.22, 0.01), mat(C.red)); f.position.set(-1.05, 0, s * 0.08); f.rotation.x = s * 0.6; arrow.add(f); }
  g.add(arrow);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1, 0.05, 8, 48), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.4, 1.6, 0.4), transparent: true, depthWrite: false }));
  g.add(ring);
  g.userData.anim = (tau) => {
    const pt = outBack(clamp(tau / 0.4), 1.6);
    tgt.scale.setScalar(Math.max(pt, 0.001));
    tgt.rotation.y = AZ;
    // la flèche arrive de la gauche de l'image, se plante, vibre
    const k = clamp((tau - 0.45) / 0.35);
    const dir = new THREE.Vector3(Math.sin(AZ), 0, Math.cos(AZ));
    const hit = new THREE.Vector3(0, 2.3, 0).addScaledVector(dir, 0.35);
    const from = hit.clone().add(new THREE.Vector3(-Math.cos(AZ) * 9, 2.2, Math.sin(AZ) * 9));
    arrow.visible = tau > 0.45;
    arrow.position.copy(from).lerp(hit, outCubic(k));
    arrow.position.y += Math.sin(k * Math.PI) * 0.6;
    const v = hit.clone().sub(from).normalize();
    arrow.rotation.set(0, Math.atan2(-v.z, v.x), 0);
    const wob = tau > 0.8 ? damped(tau - 0.8, 7, 5) * 0.12 : 0;
    arrow.rotation.z = wob;
    const pr = clamp((tau - 0.8) / 0.6);
    ring.visible = tau > 0.8 && pr < 1;
    ring.position.copy(hit); ring.rotation.set(0, AZ, 0);
    ring.scale.setScalar(0.3 + outCubic(pr) * 2.6);
    ring.material.opacity = 1 - pr;
    tgt.position.x = tau > 0.8 ? damped(tau - 0.8, 9, 8) * 0.06 : 0;
  };
  return g;
}

// ------------------------------------------------------------------ 03 : micro + bulles + ondes
function mVoice() {
  const g = new THREE.Group();
  const stand = mesh(cyl(0.09, 0.09, 2.4, 10), mat('#3A3F55')); stand.position.y = 1.2; g.add(stand);
  const foot = mesh(cyl(0.7, 0.8, 0.12, 24), mat('#3A3F55')); foot.position.y = 0.06; g.add(foot);
  const mic = new THREE.Group();
  const body = mesh(new THREE.CapsuleGeometry(0.36, 0.5, 6, 18), mat('#C9CDD8', { metalness: 0.7, roughness: 0.28 })); mic.add(body);
  const grill = mesh(sph(0.42, 20), new THREE.MeshStandardMaterial({ color: '#E7EAF0', metalness: 0.6, roughness: 0.35, wireframe: true })); grill.position.y = 0.35; mic.add(grill);
  const band = mesh(cyl(0.38, 0.38, 0.12, 20), mat(C.red)); band.position.y = -0.05; mic.add(band);
  mic.position.y = 2.75; mic.rotation.z = 0.25; mic.scale.setScalar(1.5); g.add(mic);
  const bubbles = [];
  const bc = [C.white, '#FFE3A3', '#FFD0D6'];
  [[-1.9, 3.9, 0.3], [1.8, 4.5, -0.2], [0.2, 5.4, -0.6]].forEach(([x, y, z], i) => {
    const b = new THREE.Group();
    const bb = mesh(rbox(1.5, 0.95, 0.35, 0.3), mat(bc[i], { roughness: 0.4 })); b.add(bb);
    const tail = mesh(new THREE.ConeGeometry(0.2, 0.45, 4), mat(bc[i])); tail.rotation.z = (x < 0 ? -1 : 1) * 2.6; tail.position.set(x < 0 ? 0.45 : -0.45, -0.55, 0); b.add(tail);
    for (let k = 0; k < 3; k++) { const d = mesh(sph(0.09, 10), mat(C.ink)); d.position.set(-0.35 + k * 0.35, 0, 0.2); b.add(d); }
    b.position.set(x, y, z); b.userData.i = i; g.add(b); bubbles.push(b);
  });
  const waves = [0, 1, 2].map(() => {
    const w = new THREE.Mesh(new THREE.TorusGeometry(1, 0.05, 6, 40, Math.PI * 0.9), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.6, 1.0, 2.6), transparent: true, depthWrite: false }));
    g.add(w); return w;
  });
  g.userData.anim = (tau) => {
    const pm = outBack(clamp(tau / 0.4), 1.8);
    [stand, foot].forEach((o) => o.scale.setScalar(Math.max(pm, 0.001)));
    mic.scale.setScalar(Math.max(pm, 0.001) * 1.5);
    mic.position.y = 2.75 * pm;
    stand.position.y = 1.2 * pm;
    bubbles.forEach((b) => {
      const t0 = 0.45 + b.userData.i * 0.28;
      const p = outElastic(clamp((tau - t0) / 0.6), 0.45);
      b.visible = tau > t0;
      b.scale.setScalar(Math.max(p, 0.001));
      b.rotation.y = AZ;
      b.position.y += 0;
    });
    waves.forEach((w, i) => {
      const ph = ((tau - 0.3 - i * 0.3) % 0.9) / 0.9;
      w.visible = tau > 0.3 + i * 0.3;
      w.position.set(0, 2.9, 0);
      w.rotation.set(0, AZ + Math.PI / 2, Math.PI / 2 - 0.45 + Math.PI);
      w.scale.setScalar(0.6 + ph * 2.2);
      w.material.opacity = 1 - ph;
    });
  };
  return g;
}

// ------------------------------------------------------------------ 04 : deux pièces de puzzle qui s'emboîtent
function puzzleGeo(knob) {
  const s = new THREE.Shape();
  const W = 2.0, H = 2.0, r = 0.46;
  s.moveTo(-W / 2, -H / 2);
  s.lineTo(W / 2, -H / 2);
  s.lineTo(W / 2, -r);
  if (knob) { s.absarc(W / 2 + r * 0.8, 0, r, -Math.PI * 0.7, Math.PI * 0.7, false); }
  else { s.absarc(W / 2 - r * 0.8, 0, r, -Math.PI * 0.3, Math.PI * 0.3 + Math.PI * 0.0, true); }
  s.lineTo(W / 2, H / 2);
  s.lineTo(-W / 2, H / 2);
  s.lineTo(-W / 2, -H / 2);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.45, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.08, bevelSegments: 3, curveSegments: 18 });
  g.center();
  return g;
}
function mDeal() {
  const g = new THREE.Group();
  const pair = new THREE.Group();
  const a = mesh(puzzleGeo(true), mat(C.red, { roughness: 0.4 }));
  const b = mesh(puzzleGeo(true), mat(C.gold, { roughness: 0.35, metalness: 0.2 }));
  b.rotation.z = Math.PI;
  pair.add(a); pair.add(b);
  pair.position.y = 2.0;
  g.add(pair);
  const ped = mesh(rbox(4.8, 0.4, 1.8, 0.12), mat(C.white)); ped.position.y = 0.2; g.add(ped);
  const sparks = [];
  for (let k = 0; k < 10; k++) { const s = mesh(sph(0.08, 8), glow(C.goldLight, 1.5, 3), { cast: false }); s.userData.a = (k / 10) * Math.PI * 2; g.add(s); sparks.push(s); }
  g.userData.anim = (tau) => {
    pair.rotation.y = AZ;
    const k = inOutCubic(clamp((tau - 0.15) / 0.7));
    const gap = (1 - k) * 2.4;
    a.position.set(-1.0 - gap, 0, 0);
    b.position.set(1.0 + gap + 0.37, 0, 0);
    a.position.y = (1 - k) * 0.4; b.position.y = -(1 - k) * 0.4;
    const click = tau > 0.85 ? damped(tau - 0.85, 6, 6) : 0;
    pair.scale.setScalar(1 + click * 0.12);
    pair.visible = tau > 0;
    sparks.forEach((s) => {
      const p = clamp((tau - 0.85) / 0.6);
      s.visible = tau > 0.85 && p < 1;
      const r = 0.2 + outCubic(p) * 1.8;
      s.position.set(Math.cos(s.userData.a) * r * Math.cos(AZ), 1.8 + Math.sin(s.userData.a) * r, -Math.cos(s.userData.a) * r * Math.sin(AZ));
      s.scale.setScalar(Math.max(0.001, 1 - p));
    });
    ped.scale.setScalar(Math.max(0.001, outBack(clamp(tau / 0.35))));
  };
  return g;
}

// ------------------------------------------------------------------ 05 : graphique, pièces, engrenages
function gearGeo(rOut, teeth = 10) {
  const s = new THREE.Shape();
  const rIn = rOut * 0.78;
  for (let i = 0; i < teeth * 2; i++) {
    const a0 = (i / (teeth * 2)) * Math.PI * 2, a1 = ((i + 1) / (teeth * 2)) * Math.PI * 2;
    const r = i % 2 ? rIn : rOut;
    if (i === 0) s.moveTo(Math.cos(a0) * r, Math.sin(a0) * r);
    s.lineTo(Math.cos(a0) * r, Math.sin(a0) * r);
    s.lineTo(Math.cos(a1) * r, Math.sin(a1) * r);
  }
  const hole = new THREE.Path(); hole.absarc(0, 0, rOut * 0.3, 0, Math.PI * 2, true); s.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.3, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 2 });
  g.center();
  return g;
}
function mBusiness() {
  const g = new THREE.Group();
  const bars = [[C.jade, 1.4], ['#4C7BE0', 2.2], [C.gold, 3.0], [C.red, 4.2]].map(([c, h], i) => {
    const piv = new THREE.Group(); piv.position.set(-1.5 + i * 0.95, 0, 0.4);
    const m = mesh(rbox(0.7, h, 0.7, 0.12), mat(c, { roughness: 0.45 })); m.position.y = h / 2; piv.add(m);
    piv.userData.i = i; g.add(piv); return piv;
  });
  const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(-1.9, 1.8, 1.0), new THREE.Vector3(-0.6, 2.4, 1.0), new THREE.Vector3(0.6, 3.6, 1.0), new THREE.Vector3(1.9, 5.2, 1.0)]);
  const tubeGeo = new THREE.TubeGeometry(curve, 48, 0.09, 8, false);
  const tube = mesh(tubeGeo, glow(C.red, 0.4, 2.2), { cast: false }); g.add(tube);
  const tip = mesh(new THREE.ConeGeometry(0.26, 0.55, 12), glow(C.red, 0.4, 2.2)); tip.position.copy(curve.getPoint(1)); tip.lookAt(curve.getPoint(1).add(curve.getTangent(1))); tip.rotateX(Math.PI / 2); g.add(tip);
  const coins = [];
  for (let i = 0; i < 6; i++) { const c = mesh(cyl(0.38, 0.38, 0.12, 22), mat(C.gold, { metalness: 0.75, roughness: 0.3 })); c.position.set(2.4, 0.08 + i * 0.13, -0.6); c.userData.i = i; g.add(c); coins.push(c); }
  const gears = [[1.0, 10, -1.6, 2.6, -1.4, 1], [0.7, 8, -0.35, 3.25, -1.4, -1.5]].map(([r, n, x, y, z, sp]) => {
    const m = mesh(gearGeo(r, n), mat('#9AA0B4', { metalness: 0.65, roughness: 0.32 })); m.position.set(x, y, z); m.userData.sp = sp; g.add(m); return m;
  });
  g.userData.anim = (tau) => {
    bars.forEach((b) => { const p = outBack(clamp((tau - 0.1 - b.userData.i * 0.12) / 0.45), 1.6); b.scale.set(1, Math.max(p, 0.001), 1); b.visible = p > 0.001; });
    const pr = clamp((tau - 0.55) / 0.6);
    tube.geometry.setDrawRange(0, Math.floor(tubeGeo.index.count * outCubic(pr) / 6) * 6);
    tube.visible = pr > 0;
    tip.visible = pr > 0.95; tip.scale.setScalar(Math.max(0.001, outBack(clamp((tau - 1.1) / 0.3))));
    coins.forEach((c) => { const p = clamp((tau - 0.3 - c.userData.i * 0.09) / 0.3); c.visible = p > 0; c.position.y = 0.08 + c.userData.i * 0.13 + (1 - outBounce(p)) * 3; });
    gears.forEach((m) => { m.rotation.z = tau * m.userData.sp * 1.4; m.rotation.y = AZ; m.scale.setScalar(Math.max(0.001, outBack(clamp(tau / 0.4)))); });
  };
  return g;
}

// ------------------------------------------------------------------ 06 : bambou qui pousse + sablier
function mBamboo() {
  const g = new THREE.Group();
  const stalks = [];
  [[-1.2, 0.2, 7], [0.0, -0.5, 9], [1.1, 0.4, 6]].forEach(([x, z, n], si) => {
    const st = new THREE.Group(); st.position.set(x, 0, z);
    for (let k = 0; k < n; k++) {
      const seg_ = mesh(cyl(0.15, 0.17, 0.62, 12), mat(k % 2 ? '#5DAA4F' : '#66B656', { roughness: 0.5 }));
      seg_.position.y = 0.31 + k * 0.66; seg_.userData.k = k; st.add(seg_);
      const node = mesh(cyl(0.19, 0.19, 0.06, 12), mat('#3F8A3E')); node.position.y = 0.64 + k * 0.66; node.userData.k = k; st.add(node);
      if (k > 2 && k % 2 === 1) { const lf = mesh(new THREE.ConeGeometry(0.16, 0.9, 6), mat('#7CC36A')); lf.position.set(0.35, 0.6 + k * 0.66, 0); lf.rotation.z = -1.1; lf.userData.k = k; lf.userData.leaf = true; st.add(lf); }
    }
    st.userData.n = n; st.userData.si = si; g.add(st); stalks.push(st);
  });
  const hg = new THREE.Group();
  const glassM = new THREE.MeshStandardMaterial({ color: '#DDF2FA', transparent: true, opacity: 0.45, roughness: 0.1 });
  const bulbTop = mesh(sph(0.5, 18), glassM, { cast: false }); bulbTop.scale.y = 1.1; bulbTop.position.y = 0.55; hg.add(bulbTop);
  const bulbBot = bulbTop.clone(); bulbBot.position.y = -0.55; hg.add(bulbBot);
  const capM = mat('#8B5E3C');
  for (const y of [-1.15, 1.15]) { const c = mesh(cyl(0.6, 0.6, 0.14, 20), capM); c.position.y = y; hg.add(c); }
  const sandT = mesh(new THREE.ConeGeometry(0.36, 0.5, 18), mat(C.gold)); sandT.rotation.x = Math.PI; sandT.position.y = 0.4; hg.add(sandT);
  const sandB = mesh(new THREE.ConeGeometry(0.4, 0.45, 18), mat(C.gold)); sandB.position.y = -0.85; hg.add(sandB);
  hg.position.set(2.6, 1.3, 1.2);
  g.add(hg);
  g.userData.anim = (tau) => {
    stalks.forEach((st) => {
      const n = st.userData.n;
      st.children.forEach((c) => {
        const k = c.userData.k;
        const t0 = 0.05 + st.userData.si * 0.08 + k * 0.1;
        const p = outBack(clamp((tau - t0) / 0.25), 2.0);
        c.visible = tau > t0;
        if (c.userData.leaf) c.scale.setScalar(Math.max(0.001, outElastic(clamp((tau - t0 - 0.1) / 0.5), 0.4)));
        else c.scale.set(1, Math.max(p, 0.001), 1);
      });
      st.rotation.z = 0.03 * Math.sin(tau * 2 + st.userData.si);
      void n;
    });
    const pf = inOutCubic(clamp((tau - 0.35) / 0.55));
    hg.rotation.z = Math.PI * (1 - pf);
    hg.rotation.y = AZ;
    hg.scale.setScalar(Math.max(0.001, outBack(clamp(tau / 0.35))));
    const drain = clamp((tau - 0.9) / 1.2);
    sandT.scale.setScalar(Math.max(0.001, 1 - drain * 0.8));
    sandB.scale.setScalar(0.3 + drain * 0.7);
  };
  return g;
}

// ------------------------------------------------------------------ 07 : l'équipe autour de la table, reliée
function mTeam() {
  const g = new THREE.Group();
  const table = mesh(cyl(1.3, 1.3, 0.16, 32), mat(C.white)); table.position.y = 0.75; g.add(table);
  const leg = mesh(cyl(0.12, 0.2, 0.75, 12), mat('#9AA0B4')); leg.position.y = 0.37; g.add(leg);
  const cols = [C.red, C.gold, '#4C7BE0', C.jade, '#9B6BD6', '#F07F4F'];
  const people = cols.map((c, i) => {
    const p = B.person(c);
    const a = (i / cols.length) * Math.PI * 2;
    p.position.set(Math.cos(a) * 2.0, 0, Math.sin(a) * 2.0);
    p.rotation.y = -a + Math.PI;
    p.scale.setScalar(2.2);
    p.userData.a = a; p.userData.i = i;
    g.add(p);
    return p;
  });
  const linkM = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 1.5, 0.5), transparent: true, depthWrite: false });
  const links = [];
  for (let i = 0; i < people.length; i++) for (let j = i + 1; j < people.length; j++) {
    if ((j - i) % 3 === 0 || j === i + 1 || (i === 0 && j === people.length - 1)) {
      const a = people[i].position, b = people[j].position;
      const l = beam([a.x, 1.75, a.z], [b.x, 1.75, b.z], 0.035, linkM.clone(), 6);
      l.userData.i = links.length; g.add(l); links.push(l);
    }
  }
  const star = mesh(sph(0.3, 16), glow(C.goldLight, 1.5, 3.2), { cast: false }); star.position.y = 2.6; g.add(star);
  g.userData.anim = (tau) => {
    table.scale.setScalar(Math.max(0.001, outBack(clamp(tau / 0.35))));
    leg.scale.setScalar(table.scale.x);
    people.forEach((p) => { const k = outElastic(clamp((tau - 0.15 - p.userData.i * 0.09) / 0.55), 0.45); p.visible = k > 0.001; p.scale.setScalar(2.2 * Math.max(k, 0.001)); p.userData.body.position.y = 0.28 + Math.abs(Math.sin(tau * 6 + p.userData.i)) * 0.03; });
    links.forEach((l) => { const k = clamp((tau - 0.8 - l.userData.i * 0.04) / 0.3); l.visible = k > 0; l.material.opacity = k; });
    const ps = outElastic(clamp((tau - 1.1) / 0.6), 0.4);
    star.visible = tau > 1.1; star.scale.setScalar(Math.max(0.001, ps * (1 + 0.15 * Math.sin(tau * 8))));
  };
  return g;
}

const MAKERS = [mBlocks, mTarget, mVoice, mDeal, mBusiness, mBamboo, mTeam];

export function build(ctx) {
  const { scene, T, overlay, fonts } = ctx;
  const R = rng(5);
  const islands = [];
  MODULES.forEach((p, i) => {
    const root = new THREE.Group();
    root.position.set(...p);
    scene.add(root);
    const base = islandBase(9, 9, { top: '#F1E6D6', layers: [C.earth, C.earthDark], h: [0.5, 1.0, 0.9] });
    root.add(base);
    const ring = mesh(rbox(9.1, 0.12, 9.1, 0.25), mat(MOD[i].accent, { roughness: 0.5 }), { cast: false });
    ring.position.y = -0.47; root.add(ring);
    const pad = mesh(cyl(3.3, 3.3, 0.1, 40), mat(MOD[i].accent, { roughness: 0.6 })); pad.position.y = 0.05; root.add(pad);
    const padIn = mesh(cyl(3.0, 3.0, 0.12, 40), mat('#FFF8EE', { roughness: 0.7 })); padIn.position.y = 0.06; root.add(padIn);
    // numéro gravé au sol
    const num = textMesh(fonts.title, MOD[i].n, [mat(MOD[i].accent), mat(MOD[i].accent)], { size: 1.3, depth: 0.12, bevel: 0.02 });
    num.rotation.x = -Math.PI / 2; num.rotation.z = AZ - Math.PI / 2 + Math.PI / 2; num.position.set(3.0, 0.12, 3.0);
    num.rotation.set(-Math.PI / 2, 0, AZ);
    root.add(num);
    for (let k = 0; k < 4; k++) {
      const tr = B.tree(['round', 'cherry', 'pine', 'round'][(i + k) % 4], 0.7 + R() * 0.3);
      const a = (k / 4) * Math.PI * 2 + 0.6;
      tr.position.set(Math.cos(a) * 3.9, 0, Math.sin(a) * 3.9);
      root.add(tr);
    }
    const icon = MAKERS[i]();
    root.add(icon);
    islands.push({ root, icon, i });
  });

  // chemin lumineux qui relie les stations (le parcours)
  const pts = MODULES.map((p) => new THREE.Vector3(p[0], p[1] + 0.15, p[2]));
  const curve = new THREE.CatmullRomCurve3(pts);
  const pathGeo = new THREE.TubeGeometry(curve, 240, 0.16, 8, false);
  const pathMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 1.7, 0.5) });
  const path = new THREE.Mesh(pathGeo, pathMat);
  scene.add(path);

  // médaille
  const medal = new THREE.Group();
  medal.position.set(...MEDAL);
  scene.add(medal);
  const gold = mat(C.gold, { metalness: 0.85, roughness: 0.25, emissive: '#7A5200', emissiveIntensity: 0.35 });
  const disc = mesh(cyl(6.2, 6.2, 0.9, 72), gold); disc.rotation.x = Math.PI / 2; medal.add(disc);
  const rim = mesh(new THREE.TorusGeometry(6.2, 0.5, 16, 72), gold); medal.add(rim);
  const inner = mesh(cyl(4.9, 4.9, 1.0, 72), registerGlow(new THREE.MeshStandardMaterial({ color: C.red, roughness: 0.4, emissive: C.red, emissiveIntensity: 0.25 }), 0.25, 0.6)); inner.rotation.x = Math.PI / 2; medal.add(inner);
  const glyph = textMesh(fonts.brush, '创', [registerGlow(new THREE.MeshStandardMaterial({ color: '#FFF4DE', roughness: 0.35, emissive: '#FFE9B8', emissiveIntensity: 0.6 }), 0.6, 1.1), mat(C.goldDeep)], { size: 6.4, depth: 0.6, bevel: 0.06, curve: 8 });
  glyph.position.z = 0.55; medal.add(glyph);
  const ribbon = new THREE.Group();
  for (const s of [-1, 1]) { const r = mesh(rbox(2.3, 9.0, 0.25, 0.1), mat(s < 0 ? C.red : C.gold, { roughness: 0.6 })); r.position.set(s * 1.4, 9.6, -0.5); r.rotation.z = s * 0.3; ribbon.add(r); }
  medal.add(ribbon);
  const medalShine = [];
  for (let k = 0; k < 12; k++) { const s = mesh(sph(0.18, 8), glow(C.goldLight, 2, 3.5), { cast: false }); s.userData.a = (k / 12) * Math.PI * 2; medal.add(s); medalShine.push(s); }

  // ---------------------------------------------------------------- typographie
  const head = overlay.add('modHead', `<div class="cond ink" style="font-size:26px;letter-spacing:0.3em">LE PROGRAMME</div>
     <div style="display:flex;gap:10px;margin-top:12px">${MOD.map((_, i) => `<div class="pg" style="width:46px;height:7px;border-radius:4px;background:rgba(27,30,46,0.18)"></div>`).join('')}</div>`);
  const labels = MOD.map((m, i) => overlay.add('mod' + i, `
      <div class="display" style="font-size:150px;color:transparent;-webkit-text-stroke:3px ${m.accent};line-height:0.85">${m.n}</div>
      <div class="display ink" style="font-size:96px;margin-top:6px">${Overlay.letters(m.title.toUpperCase(), 'ch m')}</div>
      <div class="body ink" style="font-size:32px;font-weight:600;margin-top:16px;opacity:0.85">${m.line}</div>`));
  const pay = overlay.add('payoff', `<div style="text-align:center">
      <div class="display ink" style="font-size:150px">${Overlay.letters('VIVRE DE SA PASSION.', 'ch p')}</div>
      <div class="body ink" style="font-size:44px;font-weight:600;margin-top:18px"><span class="ps">Devenir un créateur complet.</span></div></div>`);

  const M0 = T.modules.start, ST = T.modules.step;
  const P = T.payoff;

  function update(t) {
    const anyOn = t > M0 - 1.0 && t < P.end + 0.3;
    islands.forEach(({ root, icon, i }) => {
      root.visible = anyOn || t > T.finale.pull[0] - 0.5;
      const t0 = M0 + i * ST;
      // l'animation se joue à l'arrivée, puis l'icône reste en état final
      icon.userData.anim(t < t0 - 0.2 ? 0 : t - t0 + 0.05);
      icon.visible = t > t0 - 0.2 || t > P.start;
      if (t < t0 - 0.2 && t > P.start) icon.userData.anim(9);
    });
    // parcours
    const pp = outCubic(seg(t, P.start, P.start + 1.0));
    path.visible = (t > P.start && t < P.end + 0.3) || t > T.finale.pull[0];
    pathGeo.setDrawRange(0, Math.floor(pathGeo.index.count * (t > T.finale.pull[0] ? 1 : pp) / 3) * 3);
    // médaille
    const pm = outBack(seg(t, P.medal, P.medal + 0.8), 1.4);
    medal.visible = t > P.medal && t < P.end + 0.3;
    medal.scale.setScalar(Math.max(0.001, pm));
    medal.rotation.y = AZ + (1 - outCubic(seg(t, P.medal, P.medal + 1.4))) * Math.PI * 2 + 0.15 * Math.sin(t * 1.3);
    medal.position.y = MEDAL[1] + 0.3 * Math.sin(t * 2);
    medalShine.forEach((s) => { const a = s.userData.a + t * 0.8; s.position.set(Math.cos(a) * 7.6, Math.sin(a) * 7.6, 0.3); s.scale.setScalar(0.6 + 0.5 * Math.sin(t * 6 + s.userData.a * 3)); });
  }

  function overlayFn(t) {
    const hOn = t > M0 - 0.1 && t < M0 + 7 * ST;
    const hp = outCubic(seg(t, M0 - 0.1, M0 + 0.3)), ho = inCubic(seg(t, M0 + 7 * ST - 0.3, M0 + 7 * ST));
    style(head, { x: 134, y: 92, o: hOn ? hp * (1 - ho) : 0 });
    head.querySelectorAll('.pg').forEach((el, i) => {
      const k = clamp((t - (M0 + i * ST)) / 0.4);
      el.style.background = k > 0 ? MOD[i].accent : 'rgba(27,30,46,0.18)';
      el.style.transform = `scaleY(${1 + 0.6 * pulse(t - (M0 + i * ST), 0.03, 0.2)})`;
    });
    labels.forEach((el, i) => {
      const a = M0 + i * ST + 0.08, b = a + ST - 0.25;
      const on = t > a - 0.02 && t < b + 0.02;
      const pin = outQuart(seg(t, a, a + 0.45)), pout = inCubic(seg(t, b - 0.22, b));
      style(el, { x: 130 - pout * 80, y: 180 + (1 - pin) * 40, o: on ? pin * (1 - pout) : 0, blur: pout * 6 });
      el.querySelectorAll('.m').forEach((c, j) => { const p = outQuart(seg(t, a + 0.06 + j * 0.018, a + 0.4 + j * 0.018)); c.style.transform = `translateY(${(1 - p) * 50}px)`; c.style.opacity = String(p); });
    });
    const pa = P.start + 0.6, pb = P.end - 0.15;
    const pon = t > pa - 0.02 && t < pb + 0.02;
    const pout = inCubic(seg(t, pb - 0.3, pb));
    style(pay, { x: 960 - 800, y: 720, o: pon ? 1 - pout : 0, blur: pout * 8 });
    pay.style.width = '1600px';
    pay.querySelectorAll('.p').forEach((c, j) => { const p = outBack(seg(t, pa + j * 0.03, pa + 0.45 + j * 0.03), 1.8); c.style.transform = `translateY(${(1 - p) * 70}px) scale(${0.7 + 0.3 * p})`; c.style.opacity = String(clamp(p)); });
    const ps = pay.querySelector('.ps');
    const k = outCubic(seg(t, pa + 0.6, pa + 1.1));
    ps.style.display = 'inline-block'; ps.style.opacity = String(k); ps.style.transform = `translateY(${(1 - k) * 20}px)`;
  }

  return { update, overlay: overlayFn };
}
