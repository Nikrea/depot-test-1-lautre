// ACTE 1-2 — L'étincelle puis la ville : un cube rouge tombe dans le noir, une onde de dalles dessine une île,
// le jour se lève et une ville chinoise se construit d'elle-même.
import * as THREE from 'three';
import { C, mat, rbox, cyl, sph, mesh, compose, beam, glow } from '../core/geo.js';
import { seg, clamp, lerp, outBack, outCubic, outElastic, inCubic, inBack, outQuart, rng, wobble, window01, inOutCubic, damped } from '../core/ease.js';
import { style, Overlay } from '../core/overlay.js';
import { CITY, sp } from '../layout.js';
import * as B from './builders.js';

const HALF = 13;

export function build(ctx) {
  const { scene, T, overlay } = ctx;
  const R = rng(7);
  const root = new THREE.Group();
  root.position.set(...CITY);
  scene.add(root);
  const anims = [];
  const foot = [];
  const grow = (obj, birth, kind = 'rise', dur = 0.65) => {
    obj.userData.base = obj.scale.clone();
    obj.userData.basePos = obj.position.clone();
    anims.push({ obj, birth, kind, dur });
    return obj;
  };
  const place = (obj, x, z, ry = 0, birth = 6, kind = 'rise', r = 1.5, dur = 0.65) => {
    obj.position.set(x, 0, z);
    obj.rotation.y = ry;
    root.add(obj);
    foot.push({ x, z, r });
    return grow(obj, birth, kind, dur);
  };
  const born = (x, z, base, spread = 2.2) => base + Math.hypot(x, z) / 18 * spread + R() * 0.25;

  // ---------------------------------------------------------------- sol : dalles (onde d'apparition)
  const type = (x, z) => {
    if (Math.abs(x) < 3 && Math.abs(z) < 3) return 'plaza';
    const s = x + z;
    if (x > -4 && z > -4 && s > 9.5 && s < 12) return 'water';
    if (Math.abs(x) < 1 || Math.abs(z) < 1) return 'road';
    return 'grass';
  };
  const TILE = {
    grass: { col: [C.grass, '#93CC72'], h: 0.5, top: 0 },
    plaza: { col: ['#F1E6D6', '#E9DCC8'], h: 0.5, top: 0.02 },
    road: { col: ['#5B6178', '#565B71'], h: 0.5, top: -0.01 },
    water: { col: [C.water, '#5CC6E3'], h: 0.5, top: -0.14 },
  };
  const tiles = { grass: [], plaza: [], road: [], water: [] };
  for (let i = 0; i < 2 * HALF; i++) for (let j = 0; j < 2 * HALF; j++) {
    const x = i - HALF + 0.5, z = j - HALF + 0.5;
    const ty = type(x, z);
    tiles[ty].push({ x, z, d: Math.hypot(x, z), k: (i + j) % 2 });
  }
  const tileMeshes = [];
  const tileGeo = rbox(0.985, 0.5, 0.985, 0.07, 2);
  for (const [ty, list] of Object.entries(tiles)) {
    const im = new THREE.InstancedMesh(tileGeo, mat('#ffffff', { roughness: ty === 'water' ? 0.15 : 0.85, metalness: ty === 'water' ? 0.1 : 0 }), list.length);
    im.receiveShadow = true;
    im.castShadow = ty !== 'water';
    const col = new THREE.Color();
    list.forEach((tl, n) => { im.setColorAt(n, col.set(TILE[ty].col[tl.k])); });
    im.instanceColor.needsUpdate = true;
    im.userData = { ty, list };
    root.add(im);
    tileMeshes.push(im);
  }
  const [rp0, rp1] = T.hook.ripple;
  const tileBirth = (d) => rp0 + (d / 18) * (rp1 - rp0 - 0.4);
  let tilesFinal = false;
  const axis = new THREE.Vector3(), q = new THREE.Quaternion(), pos = new THREE.Vector3(), scl = new THREE.Vector3(), m4 = new THREE.Matrix4();
  function updateTiles(t) {
    if (t > rp1 + 0.6 && tilesFinal) return;
    for (const im of tileMeshes) {
      const { ty, list } = im.userData;
      list.forEach((tl, n) => {
        const p = seg(t, tileBirth(tl.d), tileBirth(tl.d) + 0.45);
        const y = TILE[ty].top - TILE[ty].h / 2 - (1 - outBack(p, 1.3)) * 2.6;
        axis.set(-tl.z, 0, tl.x).normalize();
        if (tl.d < 0.01) axis.set(1, 0, 0);
        q.setFromAxisAngle(axis, (1 - outCubic(p)) * Math.PI * 0.9);
        const s = p <= 0 ? 0.0001 : 0.25 + 0.75 * outCubic(p);
        pos.set(tl.x, y, tl.z); scl.set(s, s, s);
        m4.compose(pos, q, scl);
        im.setMatrixAt(n, m4);
      });
      im.instanceMatrix.needsUpdate = true;
    }
    tilesFinal = t > rp1 + 0.6;
  }

  // onde lumineuse qui accompagne l'apparition des dalles
  const ringMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 0.7, 0.4), transparent: true, opacity: 1, depthWrite: false });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1, 0.05, 8, 96), ringMat);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.08;
  root.add(ring);
  const ring2 = ring.clone();
  ring2.material = ringMat.clone();
  root.add(ring2);

  // ---------------------------------------------------------------- l'île : strates de terre qui poussent vers le bas
  const strata = [];
  const layers = [[C.earth, 1.3, 0.2], [C.earthDark, 1.1, 0.55], [C.rock, 1.0, 0.95]];
  let yy = -0.5;
  for (const [c, h, inset] of layers) {
    const piv = new THREE.Group();
    piv.position.y = yy;
    const m = mesh(rbox(2 * HALF - inset * 2, h, 2 * HALF - inset * 2, 0.3, 2), mat(c, { roughness: 0.95 }));
    m.position.y = -h / 2;
    piv.add(m);
    root.add(piv);
    strata.push(piv);
    yy -= h - 0.02;
  }
  const rocks = [];
  for (const [x, y, z, s] of [[-7, -6.2, 5, 1.2], [6, -5.6, -7, 0.9], [9, -7.0, 8, 0.7], [-9, -7.4, -6, 0.8], [2, -8.0, 9.5, 0.55]]) {
    const r = mesh(rbox(s * 1.6, s * 1.2, s * 1.4, 0.2), mat(R() > 0.5 ? C.earthDark : C.rock));
    r.position.set(x, y, z); r.rotation.y = R() * 3;
    const top = mesh(rbox(s * 1.6, 0.18, s * 1.4, 0.08), mat(C.grass)); top.position.y = s * 0.6; r.add(top);
    root.add(r); rocks.push(r);
  }

  // cascades aux deux sorties de la rivière
  const fallTex = (() => {
    const c = document.createElement('canvas'); c.width = 64; c.height = 256;
    const g = c.getContext('2d');
    const gr = g.createLinearGradient(0, 0, 0, 256); gr.addColorStop(0, '#7FD6EE'); gr.addColorStop(1, '#4FB5DA');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 256);
    for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(255,255,255,${0.25 + Math.random() * 0.4})`; g.fillRect(Math.random() * 64, Math.random() * 256, 2 + Math.random() * 3, 18 + Math.random() * 40); }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const fallMat = new THREE.MeshStandardMaterial({ map: fallTex, roughness: 0.2, transparent: true, opacity: 0.92, emissive: '#3AA7D0', emissiveIntensity: 0.15, side: THREE.DoubleSide });
  const falls = [];
  for (const [x, z, ry] of [[HALF + 0.02, -1.75, Math.PI / 2], [-1.75, HALF + 0.02, 0]]) {
    const f = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 5.2), fallMat);
    f.position.set(x, -2.75, z); f.rotation.y = ry; root.add(f); falls.push(f);
    const mist = mesh(sph(0.9, 14), mat('#FFFFFF', { transparent: true, opacity: 0.55 }), { cast: false, receive: false });
    mist.position.set(x + (ry ? 0.3 : 0), -5.4, z + (ry ? 0 : 0.3)); mist.scale.set(1.6, 0.6, 1.6); root.add(mist); falls.push(mist);
  }

  // ---------------------------------------------------------------- le cube rouge (l'étincelle)
  const cubeMat = new THREE.MeshStandardMaterial({ color: C.red, emissive: C.red, emissiveIntensity: 2.4, roughness: 0.35 });
  const cube = mesh(rbox(1.2, 1.2, 1.2, 0.16, 3), cubeMat);
  root.add(cube);
  const cubeLight = new THREE.PointLight('#FF5A4A', 30, 16, 1.6);
  root.add(cubeLight);

  // ---------------------------------------------------------------- monuments et quartiers
  const tower = B.pearlTower();
  place(tower, 0, 0, 0.3, 5.45, 'rise', 2.4, 0.9);

  // quartier d'affaires (fond)
  place(B.twistTower(13), -7.0, -7.0, 0.2, born(-7, -7, 6.0), 'rise', 2.0, 0.9);
  place(B.glassTower(2.4, 2.4, 9, { seed: 2 }), -10.0, -5.0, 0, born(-10, -5, 6.0), 'rise', 1.6);
  place(B.glassTower(2.2, 2.4, 10.5, { seed: 3, pane: '#5E8FB8' }), -4.6, -9.8, 0, born(-4.6, -9.8, 6.0), 'rise', 1.6);
  place(B.glassTower(1.8, 1.8, 7, { seed: 4, frame: '#F3E6D8', pane: '#7FA7C9' }), -9.6, -9.6, 0, born(-9.6, -9.6, 6.0), 'rise', 1.4);
  place(B.glassTower(2.0, 1.8, 5.5, { seed: 5, frame: '#F6EFE6', pane: '#86B9CF' }), -4.2, -4.0, 0, born(-4.2, -4.0, 6.0), 'rise', 1.4);
  const telecom = B.telecomTower(11);
  place(telecom, -2.4, -9.2, 0, born(-2.4, -9.2, 6.0), 'rise', 1.0);
  place(B.glassTower(1.8, 1.8, 4.2, { seed: 6 }), -7.6, -3.0, 0, born(-7.6, -3, 6.2), 'rise', 1.2);

  // quartier traditionnel (gauche)
  const pag = B.pagoda(5);
  place(pag, -7.0, 7.0, 0.0, born(-7, 7, 6.3), 'rise', 2.0, 0.9);
  place(B.courtyardHouse(2.8, 2.0), -9.9, 3.6, Math.PI / 2, born(-9.9, 3.6, 6.4), 'rise', 1.6);
  place(B.courtyardHouse(2.6, 2.0, { wall: '#F4E7D4' }), -4.4, 10.0, 0, born(-4.4, 10, 6.4), 'rise', 1.6);
  place(B.courtyardHouse(2.4, 1.9), -6.6, 3.0, 0, born(-6.6, 3.0, 6.4), 'rise', 1.5);
  place(B.courtyardHouse(2.2, 1.8, { wall: '#F7EDE0', roofCol: '#45595E' }), -9.9, 9.5, Math.PI / 2, born(-9.9, 9.5, 6.4), 'rise', 1.4);
  place(B.gate(), -4.1, 4.1, -Math.PI / 4, born(-4.1, 4.1, 6.6), 'rise', 1.2);
  const bam = B.bamboo(10, 3); place(bam, -10.2, 6.6, 0, 7.4, 'pop', 1.2);
  const bam2 = B.bamboo(7, 9); place(bam2, -7.4, 10.4, 0, 7.6, 'pop', 1.0);

  // quartier créatif (droite)
  const cine = B.cinema();
  place(cine, 6.2, -9.6, 0, born(6.2, -9.6, 6.3), 'rise', 1.9);
  const game = B.gameStudio();
  place(game, 8.9, -4.6, -Math.PI / 2, born(8.9, -4.6, 6.3), 'rise', 1.8);
  const toy = B.toyShop();
  place(toy, 4.6, -4.8, 0, born(4.6, -4.8, 6.3), 'rise', 1.8);
  const live = B.liveStudio();
  place(live, 9.6, -8.4, -Math.PI / 2, born(9.6, -8.4, 6.3), 'rise', 1.6);
  place(B.cafe('#F7D8A8'), 2.9, -8.6, 0, born(2.9, -8.6, 6.6), 'rise', 1.2);
  place(B.cafe('#CDE7D8'), 6.2, -2.4, -Math.PI / 2, born(6.2, -2.4, 6.6), 'rise', 1.1);

  // devant : rivière, ponts, monts karstiques
  const kParams = [[8.5, 8.5, 1.5, 4.6], [10.2, 6.6, 1.15, 3.5], [6.6, 10.2, 1.25, 3.9], [5.4, 7.9, 0.9, 2.6], [7.9, 5.4, 0.95, 2.8], [9.9, 9.9, 0.8, 2.3]];
  const karsts = kParams.map(([x, z, r, h], i) => {
    const k = B.karst(r, h);
    k.position.set(x, -0.6, z); root.add(k);
    foot.push({ x, z, r: r + 0.3 });
    k.userData.base = k.scale.clone(); k.userData.basePos = k.position.clone();
    anims.push({ obj: k, birth: 6.9 + i * 0.12, kind: 'rise', dur: 0.8 });
    return k;
  });
  const bridges = [];
  for (const [x, z, ry] of [[0, 10.75, 0], [10.75, 0, Math.PI / 2]]) {
    const br = new THREE.Group();
    const deck = mesh(rbox(2.2, 0.18, 3.2, 0.06), mat('#D8C7AE')); deck.position.y = 0.2; br.add(deck);
    for (const s of [-1, 1]) { const rail = mesh(rbox(0.08, 0.3, 3.2, 0.03), mat(C.red)); rail.position.set(s * 1.05, 0.42, 0); br.add(rail); }
    br.position.set(x, 0, z); br.rotation.y = ry; root.add(br);
    bridges.push(grow(br, 7.2, 'pop', 0.5));
  }
  const boat = new THREE.Group();
  { const hull = mesh(rbox(1.0, 0.22, 0.42, 0.1), mat('#8B5E3C')); boat.add(hull);
    const cab = mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.5, 12, 1, false, 0, Math.PI), mat('#C9A46B')); cab.rotation.z = Math.PI / 2; cab.rotation.y = Math.PI / 2; cab.position.y = 0.1; boat.add(cab);
    const lt = mesh(sph(0.07, 8), glow(C.red, 0.3, 2.5), { cast: false }); lt.position.set(0.45, 0.3, 0); boat.add(lt); }
  root.add(boat);

  // arbres dispersés (évite bâtiments, routes, eau, rail)
  const trees = [];
  const kinds = ['round', 'round', 'cherry', 'pine', 'round', 'gold'];
  for (let i = 0; i < 260 && trees.length < 46; i++) {
    const x = (R() * 2 - 1) * 10.4, z = (R() * 2 - 1) * 10.4;
    if (type(x, z) !== 'grass' || type(x + 0.4, z) !== 'grass' || type(x, z + 0.4) !== 'grass' || type(x - 0.4, z) !== 'grass' || type(x, z - 0.4) !== 'grass') continue;
    if (foot.some((f) => Math.hypot(f.x - x, f.z - z) < f.r + 0.7)) continue;
    if (trees.some((tr) => Math.hypot(tr.position.x - x, tr.position.z - z) < 1.0)) continue;
    const kind = x < -1 && z > 1 ? (R() > 0.5 ? 'cherry' : 'pine') : kinds[(R() * kinds.length) | 0];
    const tr = B.tree(kind, 0.8 + R() * 0.5);
    tr.position.set(x, 0, z); tr.rotation.y = R() * 6; root.add(tr);
    grow(tr, born(x, z, 7.0, 1.6), 'pop', 0.55);
    trees.push(tr);
  }

  // lanternes du quartier traditionnel
  const poles = [];
  const poleMat = mat(C.redDeep);
  const lanternRows = [[[-1.5, 2.4, 3.4], [-1.5, 2.4, 9.0]], [[-3.4, 2.4, 1.5], [-9.6, 2.4, 1.5]]];
  for (const [a, b] of lanternRows) {
    for (const p of [a, b]) { const pl = mesh(cyl(0.06, 0.07, 2.4, 8), poleMat); pl.position.set(p[0], 1.2, p[2]); root.add(pl); poles.push(grow(pl, 8.0, 'rise', 0.4)); }
    const ls = B.lanternString(a, b, 8, 0.45);
    root.add(ls);
    grow(ls, 8.2, 'drop', 0.7);
  }

  // ---------------------------------------------------------------- train à grande vitesse sur viaduc
  const A = 11.6, RC = 3.0;
  const straight = 2 * (A - RC), perim = 4 * straight + 2 * Math.PI * RC;
  const pathAt = (s) => {
    s = ((s % perim) + perim) % perim;
    const corners = [[A - RC, A - RC], [-(A - RC), A - RC], [-(A - RC), -(A - RC)], [A - RC, -(A - RC)]];
    const segLen = straight + (Math.PI / 2) * RC;
    const k = Math.floor(s / segLen), u = s - k * segLen;
    const dirs = [[-1, 0], [0, -1], [1, 0], [0, 1]];
    const starts = [[A - RC, A], [-A, A - RC], [-(A - RC), -A], [A, -(A - RC)]];
    if (u < straight) {
      const [sx, sz] = starts[k], [dx, dz] = dirs[k];
      return { x: sx + dx * u, z: sz + dz * u, h: Math.atan2(-dz, dx) };
    }
    const a0 = [Math.PI / 2, Math.PI, 1.5 * Math.PI, 0][k];
    const ang = a0 + (u - straight) / RC;
    const [cx, cz] = corners[(k + 1) % 4];
    const x = cx + Math.cos(ang) * RC, z = cz + Math.sin(ang) * RC;
    const tx = -Math.sin(ang), tz = Math.cos(ang);
    return { x, z, h: Math.atan2(-tz, tx) };
  };
  const TRACK_Y = 1.45;
  const trackPieces = [];
  const trackMat = mat('#E8E2D8');
  for (let s = 0; s < perim; s += 0.9) {
    const p = pathAt(s);
    const piece = mesh(rbox(0.95, 0.16, 0.46, 0.05), trackMat);
    piece.position.set(p.x, TRACK_Y - 0.2, p.z); piece.rotation.y = p.h; root.add(piece);
    piece.userData.s = s; trackPieces.push(piece);
    if (Math.round(s / 0.9) % 4 === 0) {
      const pil = mesh(cyl(0.11, 0.14, TRACK_Y - 0.28, 8), trackMat);
      pil.position.set(p.x, (TRACK_Y - 0.28) / 2, p.z); root.add(pil);
      pil.userData.s = s; trackPieces.push(pil);
    }
  }
  const train = [B.trainCar(true), B.trainCar(), B.trainCar(), B.trainCar()];
  train.forEach((c) => root.add(c));

  // ---------------------------------------------------------------- vie : drones, passants, cœurs du live, nuages
  const drones = [B.drone(), B.drone(), B.drone()];
  drones.forEach((d) => root.add(d));
  const people = [];
  const pcol = [C.red, C.gold, C.jade, '#4C7BE0', C.navy, '#F07F4F', C.white, '#9B6BD6'];
  for (let i = 0; i < 22; i++) {
    const p = B.person(pcol[i % pcol.length]);
    let x, z;
    if (i < 8) { x = (R() * 2 - 1) * 2.4; z = (R() * 2 - 1) * 2.4; if (Math.hypot(x, z) < 2.0) { x = 2.5 * Math.sign(x || 1); } }
    else if (i < 15) { x = (R() > 0.5 ? 1 : -1) * 1.35; z = (R() * 2 - 1) * 10; }
    else { x = (R() * 2 - 1) * 10; z = (R() > 0.5 ? 1 : -1) * 1.35; }
    p.position.set(x, 0, z);
    p.userData.path = { x, z, ax: i >= 15 ? 1 : 0, az: i >= 8 && i < 15 ? 1 : 0, amp: 0.6 + R() * 1.2, sp: 0.5 + R() * 0.6, ph: R() * 6 };
    root.add(p);
    grow(p, 8.4 + R() * 0.8, 'pop', 0.4);
    people.push(p);
  }
  const heartG = B.heartGeo();
  const hearts = [];
  for (let i = 0; i < 9; i++) {
    const h = mesh(heartG, glow(i % 3 ? '#FF4F7B' : '#FF8FAB', 0.6, 2.2), { cast: false });
    root.add(h); hearts.push(h);
  }
  const clouds = [];
  for (const [x, y, z, s, sd] of [[-17, 6, 12, 1.0, 1], [17, 8, -10, 1.2, 2], [-8, 11, -19, 1.1, 3], [18, 2.5, 16, 0.8, 4], [-20, 1, -4, 0.8, 5], [2, 13, 19, 0.9, 6]]) {
    const c = B.cloud(sd); c.position.set(x, y, z); c.scale.setScalar(s); c.userData.home = [x, y, z]; root.add(c); clouds.push(c);
  }

  // repères pour les cartes de chiffres
  const wp = (obj, dy) => { const v = new THREE.Vector3(); obj.getWorldPosition(v); return [v.x, v.y + dy, v.z]; };
  ctx.anchors = {
    telecom: () => wp(telecom, telecom.userData.top),
    cinema: () => wp(cine, 4.6),
    game: () => wp(game, 4.4),
    toy: () => wp(toy, 3.8),
    center: () => [CITY[0], 6, CITY[2]],
  };
  ctx.city = { root, live, hearts, cine, game, toy, telecom };

  // ---------------------------------------------------------------- typographie
  const L1 = overlay.add('hook1', Overlay.words("ET SI TON TERRAIN DE JEU"), 'display white');
  L1.style.fontSize = '104px';
  const L2 = overlay.add('hook2', Overlay.words("ÉTAIT À L'AUTRE BOUT DU MONDE ?"), 'display white');
  L2.style.fontSize = '104px';
  const tWrap = overlay.add('cityTitle', `
      <div class="brush red" style="font-size:150px;line-height:1;margin-left:6px">中国</div>
      <div class="display ink" style="font-size:230px;margin-top:-6px">${Overlay.letters('LA CHINE', 'ch t')}</div>
      <div class="body ink" style="font-size:38px;font-weight:600;margin-top:22px;white-space:normal;width:640px;line-height:1.25">
        <span class="sub">Le plus grand terrain de jeu créatif de la planète.</span></div>`, '');

  function textHook(t) {
    const [a1, b1] = T.hook.line1, [a2, b2] = T.hook.line2;
    const words = (el, a, b, y0) => {
      const ws = el.querySelectorAll('.wi');
      const W = el.offsetWidth;
      style(el, { x: 960 - W / 2, y: y0, o: t > a - 0.1 && t < b + 0.1 ? 1 : 0 });
      ws.forEach((w, i) => {
        const p = outQuart(seg(t, a + i * 0.09, a + i * 0.09 + 0.5));
        const out = inCubic(seg(t, b - 0.35, b));
        w.style.transform = `translateY(${(1 - p) * 110 + out * -110}%)`;
      });
    };
    words(L1, a1, b1, 800);
    words(L2, a2, b2, 800);
  }

  function textTitle(t) {
    const [a, b] = T.city.title;
    const on = t > a - 0.1 && t < b + 0.2;
    const o = on ? 1 : 0;
    const out = inCubic(seg(t, b - 0.45, b));
    style(tWrap, { x: 130 - out * 120, y: 190, o: o * (1 - out), blur: out * 10 });
    const br = tWrap.querySelector('.brush');
    const pb = outBack(seg(t, a, a + 0.6), 2.2);
    br.style.transform = `scale(${0.4 + 0.6 * pb}) rotate(${(1 - pb) * -12}deg)`;
    br.style.opacity = String(clamp(pb * 1.5));
    tWrap.querySelectorAll('.t').forEach((el, i) => {
      const p = outQuart(seg(t, a + 0.18 + i * 0.05, a + 0.18 + i * 0.05 + 0.55));
      el.style.transform = `translateY(${(1 - p) * 60}px) skewX(${(1 - p) * -10}deg)`;
      el.style.opacity = String(p);
    });
    const sub = tWrap.querySelector('.sub');
    const ps = outCubic(seg(t, T.city.sub[0], T.city.sub[0] + 0.7));
    sub.style.opacity = String(ps);
    sub.style.display = 'inline-block';
    sub.style.transform = `translateY(${(1 - ps) * 24}px)`;
  }

  // ---------------------------------------------------------------- animation
  function update(t) {
    root.visible = t < 46.5 || t > T.finale.pull[0] - 0.5;
    updateTiles(t);

    // anneaux d'impact
    const land = T.hook.cubeLand;
    for (const [rg, delay] of [[ring, 0], [ring2, 0.18]]) {
      const p = seg(t, land + delay, land + delay + 1.6);
      rg.visible = p > 0 && p < 1;
      rg.scale.setScalar(0.6 + outCubic(p) * 17);
      rg.material.opacity = (1 - p) * (1 - p);
    }

    // strates
    const [g0, g1] = T.hook.baseGrow;
    strata.forEach((s, i) => { const p = outCubic(seg(t, g0 + i * 0.25, g0 + i * 0.25 + 1.3)); s.scale.y = Math.max(p, 0.0001); s.visible = p > 0.001; });
    rocks.forEach((r, i) => {
      const p = outBack(seg(t, g0 + 1.0 + i * 0.12, g0 + 1.6 + i * 0.12));
      r.scale.setScalar(Math.max(p, 0.0001)); r.visible = p > 0.001;
      r.position.y += 0; r.rotation.y += 0;
      r.position.y = [-6.2, -5.6, -7.0, -7.4, -8.0][i] + 0.25 * Math.sin(t * 0.8 + i * 1.7);
    });
    falls.forEach((f, i) => {
      const p = seg(t, 7.0, 7.8);
      f.visible = p > 0;
      if (i % 2 === 0) { f.scale.y = Math.max(p, 0.001); f.position.y = -2.75 * p + 0 * (1 - p); }
      else f.scale.setScalar(Math.max(0.001, outBack(seg(t, 7.6, 8.2))) );
    });
    fallTex.offset.y = t * 1.3;

    // cube
    const [d0] = [T.hook.cubeDrop];
    const pf = seg(t, d0, land);
    const tau = t - land;
    let cy = 0.62 + 6.5 * (1 - pf * pf);
    let sy = 1, sxz = 1;
    if (tau > 0) { sy = 1 - 0.38 * Math.exp(-tau / 0.09) * Math.cos(2 * Math.PI * 4.5 * tau); sxz = 1 / Math.sqrt(sy); cy = 0.62 * sy; }
    const [k0, k1] = T.hook.cubeSink;
    const ps = seg(t, k0, k1);
    cy -= inBack(ps, 1.4) * 1.6;
    const sk = 1 - inCubic(ps) * 0.5;
    cube.position.set(0, cy, 0);
    cube.scale.set(sxz * sk, sy * sk, sxz * sk);
    cube.rotation.set(tau < 0 ? (1 - pf) * 0.9 : 0, tau < 0 ? (1 - pf) * 5.5 : 0.18 * wobble(t, 1, 0.4), 0);
    cube.visible = t > d0 && ps < 1;
    const dayK = seg(t, 4.2, 6.2);
    cubeMat.emissiveIntensity = (1.3 + 0.3 * Math.sin(t * 5)) * (1 - dayK) + 0.25;
    cubeLight.position.set(0, cy + 0.8, 0);
    cubeLight.intensity = (t > d0 ? 22 : 0) * (1 - dayK) * (1 - ps) + (tau > 0 ? 30 * Math.exp(-tau / 0.25) : 0);

    // croissance des objets
    for (const a of anims) {
      const { obj, birth, kind, dur } = a;
      const p = seg(t, birth, birth + dur);
      const bs = obj.userData.base, bp = obj.userData.basePos;
      obj.visible = p > 0.0005;
      if (!obj.visible) continue;
      if (kind === 'rise') {
        const e = outBack(p, 1.25);
        obj.scale.set(bs.x * (0.65 + 0.35 * outCubic(p)), bs.y * Math.max(e, 0.001), bs.z * (0.65 + 0.35 * outCubic(p)));
        obj.position.y = bp.y;
      } else if (kind === 'pop') {
        const e = outElastic(p, 0.45);
        obj.scale.set(bs.x * Math.max(e, 0.001), bs.y * Math.max(e, 0.001), bs.z * Math.max(e, 0.001));
      } else if (kind === 'drop') {
        obj.position.y = bp.y + (1 - outCubic(p)) * 4;
        obj.scale.copy(bs);
      }
    }

    // train
    const tp = seg(t, 7.0, 8.3);
    trackPieces.forEach((pc) => { const k = seg(tp, pc.userData.s / perim - 0.05, pc.userData.s / perim + 0.05); pc.visible = k > 0; pc.scale.setScalar(Math.max(outBack(k), 0.001)); });
    const trainOn = seg(t, T.city.train, T.city.train + 0.5);
    const s0 = 6.5 * (t - T.city.train) + 10;
    train.forEach((c, i) => {
      const p = pathAt(s0 - i * 1.42);
      c.position.set(p.x, TRACK_Y + 0.08, p.z); c.rotation.y = p.h;
      c.visible = trainOn > 0; c.scale.setScalar(Math.max(outBack(trainOn), 0.001));
    });

    // drones
    drones.forEach((d, i) => {
      const p = outCubic(seg(t, T.city.drones + i * 0.25, T.city.drones + 0.9 + i * 0.25));
      const bx = [-7.5, -3.5, -9.0][i], bz = [-8.5, -6.5, -3.5][i], by = [14.2, 11.6, 10.5][i];
      d.visible = p > 0;
      d.position.set(bx + 0.6 * Math.sin(t * 0.7 + i), lerp(by - 5, by, p) + 0.25 * Math.sin(t * 2.2 + i * 2), bz + 0.6 * Math.cos(t * 0.6 + i));
      d.rotation.y = t * 0.3 + i;
      d.userData.lights.forEach((l, j) => { l.visible = Math.sin(t * 6 + i + j * 3) > 0; });
    });

    // passants
    for (const p of people) {
      const pa = p.userData.path;
      const u = Math.sin(t * pa.sp + pa.ph) * pa.amp;
      p.position.x = pa.x + (pa.ax ? u : 0);
      p.position.z = pa.z + (pa.az ? u : 0);
      p.rotation.y = pa.ax ? (Math.cos(t * pa.sp + pa.ph) > 0 ? 0 : Math.PI) : (Math.cos(t * pa.sp + pa.ph) > 0 ? -Math.PI / 2 : Math.PI / 2);
      p.userData.body.position.y = 0.28 + Math.abs(Math.sin(t * 9 + pa.ph)) * 0.04;
    }

    // bateau sur la rivière
    const bu = ((t * 0.08) % 1);
    const bx = lerp(-1.5, 11.2, bu);
    boat.position.set(bx, -0.08, 10.75 - bx + 0.0);
    boat.rotation.y = Math.PI / 4;
    boat.visible = t > 7.4;

    // cœurs du live
    hearts.forEach((h, i) => {
      const per = 2.2, ph = (t + i * per / hearts.length) % per / per;
      const on = t > 8.6;
      h.visible = on;
      const base = live.position;
      h.position.set(base.x + 0.9 + Math.sin(i * 2.1 + t * 2) * 0.35, 3.0 + ph * 3.2, base.z + Math.cos(i * 1.3) * 0.4);
      const s = Math.sin(ph * Math.PI) * 0.55;
      h.scale.setScalar(Math.max(s, 0.001));
      h.rotation.y = Math.PI / 4;
    });

    // éléments vivants des bâtiments
    cine.userData.reel.rotation.z = t * 1.2;
    game.userData.pad.rotation.z = 0.12 * Math.sin(t * 2.4);

    clouds.forEach((c, i) => {
      const [x, y, z] = c.userData.home;
      c.position.set(x + Math.sin(t * 0.08 + i) * 1.5 + t * 0.06, y + Math.sin(t * 0.3 + i) * 0.2, z);
      const p = outCubic(seg(t, 5.0 + i * 0.15, 6.5 + i * 0.15));
      c.visible = p > 0;
      c.scale.setScalar(Math.max(0.001, [1.0, 1.2, 1.1, 0.8, 0.8, 0.9][i] * p));
    });
  }

  function overlayFn(t) {
    textHook(t);
    textTitle(t);
  }

  return { update, overlay: overlayFn };
}
