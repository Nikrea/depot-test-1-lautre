// ACTE 6 — Final : l'archipel de nuit, feux d'artifice, signature et sceau 创.
import * as THREE from 'three';
import { C } from '../core/geo.js';
import { seg, clamp, outBack, outCubic, outQuart, inCubic, rng, damped } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { sp } from '../layout.js';

export function build(ctx) {
  const { scene, T, overlay } = ctx;
  const R = rng(2026);
  const F = T.finale;

  // feux d'artifice (étincelles instanciées, gravité, fondu)
  const bursts = [
    [56.4, sp(-2, 8, 26), '#FFD27A'], [57.1, sp(30, 52, 30), '#FF4F6D'], [57.6, sp(56, 24, 24), '#29F0E4'],
    [58.3, sp(-30, 50, 28), '#FFD27A'], [59.0, sp(14, 30, 34), '#FF8A2A'], [59.8, sp(44, 64, 30), '#FFFFFF'], [60.4, sp(4, 40, 30), '#FF4F6D'],
  ];
  const N = 70;
  const geo = new THREE.SphereGeometry(0.32, 6, 4);
  const fw = bursts.map(([t0, p, col]) => {
    const m = new THREE.InstancedMesh(geo, new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(4.0), transparent: true, depthWrite: false }), N);
    m.frustumCulled = false;
    const dirs = Array.from({ length: N }, () => { const u = R() * 2 - 1, a = R() * Math.PI * 2, r = Math.sqrt(1 - u * u); return new THREE.Vector3(r * Math.cos(a), u, r * Math.sin(a)).multiplyScalar(0.8 + R() * 0.4); });
    scene.add(m);
    return { m, t0, p, dirs };
  });
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3();

  // typographie de fin
  const veil = overlay.add('fVeil', `<div style="width:1920px;height:1080px;background:radial-gradient(ellipse at 50% 46%, rgba(6,8,24,0.62) 0%, rgba(6,8,24,0.25) 45%, rgba(6,8,24,0) 70%)"></div>`);
  const lock = overlay.add('fLock', `<div style="text-align:center">
      <div class="display white" style="font-size:210px">${Overlay.letters('CREATOR', 'ch z1')}</div>
      <div class="display" style="font-size:96px;color:#FFD27A;margin:2px 0 -2px">${Overlay.letters('IS THE NEW', 'ch z2')}</div>
      <div class="display red" style="font-size:210px;text-shadow:0 0 30px rgba(226,53,59,0.45)">${Overlay.letters('ATHLETE', 'ch z3')}</div></div>`);
  const cta = overlay.add('fCta', `<div style="text-align:center">
      <div class="body white" style="font-size:40px;font-weight:600"><span class="c1">Ta passion. Ton terrain de jeu. Ton futur.</span></div>
      <div class="cond" style="font-size:26px;letter-spacing:0.3em;color:rgba(251,247,242,0.75);margin-top:16px"><span class="c2">FORMATION &amp; ACCOMPAGNEMENT · NIK &amp; ODYO</span></div></div>`);
  const seal = overlay.add('fSeal', '<div class="seal"><span>创</span></div>');

  function update(t) {
    fw.forEach(({ m, t0, p, dirs }) => {
      const tau = t - t0;
      const on = tau > 0 && tau < 2.2;
      m.visible = on;
      if (!on) return;
      const k = outCubic(clamp(tau / 1.1));
      dirs.forEach((d, i) => {
        v.set(p[0] + d.x * 11 * k, p[1] + d.y * 11 * k - 2.2 * tau * tau, p[2] + d.z * 11 * k);
        sc.setScalar(Math.max(0.001, (1 - clamp(tau / 2.2)) * (0.7 + 0.6 * ((i * 7) % 5) / 5)));
        m4.compose(v, q, sc);
        m.setMatrixAt(i, m4);
      });
      m.instanceMatrix.needsUpdate = true;
      m.material.opacity = 1 - inCubic(clamp((tau - 1.2) / 1.0));
    });
  }

  function overlayFn(t) {
    const a = F.pull[1] - 1.0;
    const on = t > a - 0.05;
    style(veil, { o: on ? outCubic(seg(t, a, a + 0.8)) : 0 });
    style(lock, { x: 960 - 700, y: 150, o: on ? 1 : 0 });
    lock.style.width = '1400px';
    const lines = [['.z1', a], ['.z2', a + 0.35], ['.z3', a + 0.55]];
    for (const [cls, t0] of lines) lock.querySelectorAll(cls).forEach((c, i) => {
      const p = outBack(seg(t, t0 + i * 0.03, t0 + 0.5 + i * 0.03), 1.8);
      c.style.opacity = String(clamp(p * 1.2));
      c.style.transform = `translateY(${(1 - p) * 90}px) scale(${0.7 + 0.3 * p}) skewX(${(1 - p) * -12}deg)`;
    });
    style(cta, { x: 960 - 700, y: 820, o: t > F.cta - 0.05 ? 1 : 0 });
    cta.style.width = '1400px';
    for (const [cls, t0] of [['.c1', F.cta], ['.c2', F.cta + 0.45]]) {
      const el = cta.querySelector(cls), k = outQuart(seg(t, t0, t0 + 0.55));
      el.style.display = 'inline-block'; el.style.opacity = String(k); el.style.transform = `translateY(${(1 - k) * 24}px)`;
    }
    const st = F.stamp;
    const ps = seg(t, st - 0.18, st);
    const imp = damped(t - st, 7, 9);
    style(seal, { x: 1580, y: 150, o: t > st - 0.18 ? Math.min(1, ps * 2) : 0, s: 2.6 - 1.6 * outCubic(ps) - 0.08 * imp, r: -8 + (1 - ps) * 20 });
  }

  function post(t, { fin }) {
    fin.uniforms.uFade.value = Math.max(fin.uniforms.uFade.value, inCubic(seg(t, F.fade[0], F.fade[1])));
  }

  function camera(t, s) {
    const imp = damped(t - F.stamp, 8, 9) * 0.01;
    s.shake[1] += imp;
  }

  return { update, overlay: overlayFn, post, camera };
}
