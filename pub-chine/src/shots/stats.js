// ACTE 2b — Les chiffres (sources vérifiées) puis l'Eldorado : pluie de pièces d'or sur la ville.
import * as THREE from 'three';
import { C, mat, cyl, mesh } from '../core/geo.js';
import { seg, clamp, outBack, outCubic, outQuart, inCubic, outElastic, rng, damped } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { CITY } from '../layout.js';

const CARDS = [
  { key: 'telecom', tag: 'Internet', to: 1.12, fmt: (v) => v.toFixed(2).replace('.', ',') + ' Md', lbl: "d'internautes en Chine", src: 'CNNIC, déc. 2025', x: 110, y: 96 },
  { key: 'cinema', tag: 'Animation', to: 2.2, fmt: (v) => v.toFixed(1).replace('.', ',') + ' Md $', lbl: "au box-office pour <b>Ne Zha 2</b>, record mondial du film d'animation", src: 'Guinness World Records', x: 1490, y: 96 },
  { key: 'game', tag: 'Jeu vidéo', to: 10, fmt: (v) => Math.round(v) + ' M', lbl: 'de copies de <b>Black Myth: Wukong</b> vendues en 3 jours', src: 'Game Science, août 2024', x: 1490, y: 420 },
  { key: 'toy', tag: 'Design & jouets', to: 185, fmt: (v) => '+' + Math.round(v) + ' %', lbl: "de chiffre d'affaires pour <b>Pop Mart</b> (Labubu) en 2025", src: 'Pop Mart, résultats 2025', x: 1490, y: 744 },
];

export function build(ctx) {
  const { scene, T, overlay, rig } = ctx;
  const R = rng(99);

  // ---------------------------------------------------------------- 3D : ondes du relais télécom, pièces d'or
  const waveMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.8, 0.35, 0.3), transparent: true, depthWrite: false });
  const waves = [0, 1, 2].map(() => {
    const w = new THREE.Mesh(new THREE.TorusGeometry(1, 0.045, 8, 64), waveMat.clone());
    w.rotation.x = Math.PI / 2; scene.add(w); return w;
  });

  const coinGeo = cyl(0.42, 0.42, 0.09, 24);
  const coinMat = mat(C.gold, { metalness: 0.85, roughness: 0.28, emissive: '#B8860B', emissiveIntensity: 0.35 });
  const N = 230;
  const coins = new THREE.InstancedMesh(coinGeo, coinMat, N);
  coins.castShadow = false;
  scene.add(coins);
  const cdat = Array.from({ length: N }, () => ({
    x: (R() * 2 - 1) * 12, z: (R() * 2 - 1) * 12, y0: 0.5 + R() * 6, d: R() * 1.3, sp: 4.5 + R() * 4.5, rot: R() * 6, rs: 3 + R() * 6,
  }));
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3();

  // ---------------------------------------------------------------- typographie
  const svg = overlay.add('statsLines', `<svg width="1920" height="1080" style="overflow:visible">${CARDS.map((_, i) =>
    `<line id="ln${i}" stroke="#1B1E2E" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="1400" stroke-dashoffset="1400"/>`).join('')}</svg>`);
  const dots = CARDS.map((_, i) => overlay.add('dot' + i, '<div class="dot"></div>'));
  const cards = CARDS.map((c, i) => overlay.add('card' + i,
    `<div class="card"><div class="tag">${c.tag}</div><div class="num">0</div><div class="lbl">${c.lbl}</div>
      <div class="src">Source : ${c.src}</div></div>`));
  const eld = overlay.add('eldorado', `<div style="text-align:center">
      <div class="display red" style="font-size:190px">${Overlay.letters("L'ELDORADO", 'ch e')}</div>
      <div class="display ink" style="font-size:96px;margin-top:4px">${Overlay.letters('DES CRÉATEURS', 'ch e2')}</div></div>`);

  const cardIn = (i) => T.stats.cards[i];
  const OUT = T.stats.end;

  function update(t) {
    const anchors = ctx.anchors;
    // ondes du relais (carte 1)
    const top = anchors.telecom();
    waves.forEach((w, i) => {
      const a = cardIn(0) + i * 0.35;
      const ph = ((t - a) % 1.05) / 1.05;
      const on = t > a && t < OUT;
      w.visible = on;
      w.position.set(top[0], top[1] - 0.2, top[2]);
      w.scale.setScalar(0.3 + ph * 4.5);
      w.material.opacity = on ? (1 - ph) * 0.9 : 0;
    });
    // réactions des bâtiments
    const { game, toy, cine } = ctx.city;
    const pg = damped(t - cardIn(2), 3.2, 4.5);
    game.userData.pad.scale.setScalar(1 + 0.25 * pg);
    const pt = damped(t - cardIn(3), 3.0, 4.0);
    toy.scale.y = toy.userData.base ? toy.userData.base.y * (1 + 0.12 * pt) : 1;
    cine.userData.reel.rotation.z += t > cardIn(1) && t < OUT ? (t - cardIn(1)) * 4 : 0;

    // pluie d'or (Eldorado)
    const e0 = T.eldorado.start;
    const on = t > e0 && t < 23.2;
    coins.visible = on;
    if (on) {
      cdat.forEach((c, i) => {
        const tau = t - e0 - c.d;
        const y = c.y0 + (tau > 0 ? tau * c.sp - 0.9 * tau * tau : -50);
        const s = tau > 0 ? outBack(clamp(tau / 0.3)) * (1 - inCubic(seg(tau, 1.6, 2.4))) : 0;
        e.set(0.5 + Math.sin(i), c.rot + tau * c.rs, 0.3);
        q.setFromEuler(e);
        p3.set(CITY[0] + c.x, CITY[1] + y, CITY[2] + c.z);
        s3.setScalar(Math.max(s, 0.0001));
        m4.compose(p3, q, s3);
        coins.setMatrixAt(i, m4);
      });
      coins.instanceMatrix.needsUpdate = true;
    }
  }

  function overlayFn(t) {
    const anchors = ctx.anchors;
    CARDS.forEach((c, i) => {
      const a = cardIn(i);
      const vis = t > a - 0.05 && t < OUT + 0.05;
      const pin = outBack(seg(t, a, a + 0.55), 1.6);
      const out = inCubic(seg(t, OUT - 0.45 + i * 0.06, OUT - 0.1 + i * 0.06));
      const card = cards[i];
      style(card, { x: c.x, y: c.y + (1 - pin) * 40 + out * 30, o: vis ? clamp(pin * 1.4) * (1 - out) : 0, s: 0.82 + 0.18 * pin });
      const v = c.to * outQuart(seg(t, a + 0.1, a + 1.1));
      card.querySelector('.num').textContent = c.fmt(v);
      // repère + ligne
      const [ax, ay] = rig.project(anchors[c.key]());
      const pd = outElastic(seg(t, a - 0.1, a + 0.6), 0.4);
      style(dots[i], { x: ax - 9, y: ay - 9, o: vis ? clamp(pd) * (1 - out) : 0, s: Math.max(pd, 0.01) });
      const ln = svg.querySelector('#ln' + i);
      const cx = c.x < 960 ? c.x + 360 : c.x - 8, cy = c.y + 70;
      ln.setAttribute('x1', ax); ln.setAttribute('y1', ay); ln.setAttribute('x2', cx); ln.setAttribute('y2', cy);
      const len = Math.hypot(cx - ax, cy - ay);
      ln.setAttribute('stroke-dasharray', String(len));
      ln.setAttribute('stroke-dashoffset', String(len * (1 - outCubic(seg(t, a - 0.05, a + 0.45)))));
      ln.style.opacity = vis ? String(1 - out) : '0';
    });
    style(svg, { o: t > cardIn(0) - 0.1 && t < OUT + 0.1 ? 1 : 0 });

    // Eldorado
    const [ea, eb] = T.eldorado.title;
    const eo = t > ea - 0.05 && t < eb + 0.1 ? 1 : 0;
    const eout = inCubic(seg(t, eb - 0.35, eb));
    style(eld, { x: 960 - 560, y: 70 - eout * 40, o: eo * (1 - eout), blur: eout * 8 });
    eld.style.width = '1120px';
    eld.querySelectorAll('.e').forEach((el, i) => {
      const p = outBack(seg(t, ea + i * 0.035, ea + i * 0.035 + 0.5), 2.0);
      el.style.transform = `translateY(${(1 - p) * 80}px) scale(${0.6 + 0.4 * p})`;
      el.style.opacity = String(clamp(p * 1.3));
    });
    eld.querySelectorAll('.e2').forEach((el, i) => {
      const p = outQuart(seg(t, ea + 0.35 + i * 0.03, ea + 0.35 + i * 0.03 + 0.5));
      el.style.transform = `translateY(${(1 - p) * 40}px)`;
      el.style.opacity = String(p);
    });
  }

  return { update, overlay: overlayFn };
}
