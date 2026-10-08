// Point d'entrée : scène, lumière, temps qu'il fait, caméra globale, rendu image par image.
import * as THREE from 'three';
import { Rig, ISO_EL } from './core/rig.js';
import { makeComposer } from './core/post.js';
import { Overlay } from './core/overlay.js';
import { loadFont } from './core/text3d.js';
import { setNight } from './core/geo.js';
import { pchip, seg, smooth } from './core/ease.js';
import { AZ } from './layout.js';
import * as hookCity from './shots/city.js';
import * as stats from './shots/stats.js';
import * as brand from './shots/brand.js';
import * as modules from './shots/modules.js';
import * as founders from './shots/founders.js';
import * as finale from './shots/finale.js';
import { cameraKeys } from './camera.js';

const Q = new URLSearchParams(location.search);
const W = +(Q.get('w') || 1920), H = +(Q.get('h') || 1080);

const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
const stage = document.getElementById('stage');
stage.style.width = W + 'px';
stage.style.height = H + 'px';
stage.prepend(renderer.domElement);
const ovRoot = document.getElementById('ov');
ovRoot.style.transform = `scale(${W / 1920})`;

const scene = new THREE.Scene();
const rig = new Rig(W, H);
scene.add(rig.cam);
const { composer, bloom, blur, fin } = makeComposer(renderer, scene, rig.cam, W, H);
const overlay = new Overlay(ovRoot);

// ---------------------------------------------------------------- ciel (dégradé + étoiles), attaché à la caméra
const skyMat = new THREE.ShaderMaterial({
  depthWrite: false, depthTest: false,
  uniforms: {
    uTop: { value: new THREE.Color() }, uBot: { value: new THREE.Color() }, uGlow: { value: new THREE.Color() },
    uGlowPos: { value: new THREE.Vector2(0.5, 0.35) }, uStars: { value: 0 }, uTime: { value: 0 }, uAsp: { value: W / H },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.9999, 1.0); }`,
  fragmentShader: `
    uniform vec3 uTop, uBot, uGlow; uniform vec2 uGlowPos; uniform float uStars, uTime, uAsp; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    void main(){
      vec3 c = mix(uBot, uTop, smoothstep(0.0, 1.0, vUv.y));
      vec2 d = (vUv - uGlowPos) * vec2(uAsp, 1.0);
      c += uGlow * exp(-dot(d, d) * 2.2);
      if (uStars > 0.0) {
        vec2 g = vUv * vec2(uAsp, 1.0) * 90.0; vec2 id = floor(g); vec2 f = fract(g) - 0.5;
        float r = h(id); float s = step(0.985, r) * smoothstep(0.09, 0.0, length(f - (vec2(h(id + 3.1), h(id + 7.7)) - 0.5) * 0.6));
        s *= 0.55 + 0.45 * sin(uTime * (1.5 + r * 3.0) + r * 40.0);
        c += vec3(0.9, 0.92, 1.0) * s * uStars * smoothstep(0.2, 0.9, vUv.y);
      }
      gl_FragColor = vec4(c, 1.0);
    }`,
});
const sky = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), skyMat);
sky.frustumCulled = false;
sky.renderOrder = -1000;
scene.add(sky);

// ---------------------------------------------------------------- lumières
const hemi = new THREE.HemisphereLight('#fff', '#888', 1);
scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff', 3);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02;
sun.shadow.radius = 3;
scene.add(sun);
scene.add(sun.target);

// ---------------------------------------------------------------- temps qu'il fait (aube -> jour -> heure dorée -> crépuscule -> nuit)
const ENV = [
  // t,   ciel haut, ciel bas,  halo,      soleil,   I,   élév, hémi ciel, hémi sol, hI,  nuit, bloom, étoiles
  [0.0, '#05060C', '#0B0D18', '#1A0A0C', '#FFE9D6', 0.15, 50, '#2A2E44', '#120E0C', 0.18, 0.0, 0.5, 0.0],
  [4.3, '#05060C', '#0B0D18', '#2A0C10', '#FFE9D6', 0.15, 50, '#2A2E44', '#120E0C', 0.18, 0.0, 0.5, 0.0],
  [6.4, '#F2C9A8', '#FCEFE2', '#FFF4E4', '#FFF1DD', 3.5, 50, '#FFF3E6', '#B89272', 0.85, 0.0, 0.35, 0.0],
  [19.4, '#F2C9A8', '#FCEFE2', '#FFF4E4', '#FFF1DD', 3.5, 50, '#FFF3E6', '#B89272', 0.85, 0.0, 0.35, 0.0],
  [21.2, '#EE9F5C', '#FFE4BC', '#FFD9A0', '#FFC27A', 3.5, 24, '#FFE6C7', '#B98656', 1.0, 0.0, 0.45, 0.0],
  [27.6, '#EFA879', '#FDE6CB', '#FFE0B8', '#FFC890', 3.0, 30, '#FFEBD6', '#B98A66', 1.05, 0.0, 0.4, 0.0],
  [36.0, '#D97F8E', '#FFC7A3', '#FFD0B0', '#FF9C6B', 2.5, 15, '#F7C6B8', '#8A5A6A', 0.95, 0.12, 0.45, 0.0],
  [43.6, '#4B3676', '#E2878C', '#F2A0A0', '#D98BC9', 1.25, 11, '#9A86C9', '#4A3A5A', 0.62, 0.55, 0.6, 0.25],
  [47.2, '#060A22', '#1F1648', '#3A2A6A', '#8FA8FF', 0.8, 48, '#3A4A8F', '#1C1630', 0.5, 1.0, 0.5, 1.0],
  [62.0, '#060A22', '#1F1648', '#3A2A6A', '#8FA8FF', 0.8, 48, '#3A4A8F', '#1C1630', 0.5, 1.0, 0.5, 1.0],
];
const _c1 = new THREE.Color(), _c2 = new THREE.Color();
function lerpColor(a, b, k) { return _c1.set(a).lerp(_c2.set(b), k).clone(); }

export function env(t) {
  let i = 0;
  while (i < ENV.length - 2 && t > ENV[i + 1][0]) i++;
  const A = ENV[i], B = ENV[i + 1];
  const k = smooth(seg(t, A[0], B[0]));
  const num = (j) => A[j] + (B[j] - A[j]) * k;
  return {
    top: lerpColor(A[1], B[1], k), bot: lerpColor(A[2], B[2], k), glow: lerpColor(A[3], B[3], k),
    sun: lerpColor(A[4], B[4], k), sunI: num(5), sunEl: num(6),
    hemiSky: lerpColor(A[7], B[7], k), hemiGround: lerpColor(A[8], B[8], k), hemiI: num(9),
    night: num(10), bloom: num(11), stars: num(12),
  };
}

// ---------------------------------------------------------------- démarrage
const T = await (await fetch('timeline.json')).json();
const fonts = {
  title: await loadFont('assets/fonts/BarlowCondensed-BlackItalic.ttf'),
  brush: await loadFont('assets/fonts/MaShanZheng-sub.ttf'),
};
const texLoader = new THREE.TextureLoader();
const photos = await Promise.all([7, 8, 9, 10, 11].map((i) => texLoader.loadAsync(`assets/photos/photo_${i}.jpg`)));
photos.forEach((p) => { p.colorSpace = THREE.SRGBColorSpace; p.anisotropy = 8; });
await Promise.all(['900 italic 100px "Barlow Condensed"', '700 100px "Barlow Condensed"', '100px MaShan', '600 40px Inter'].map((f) => document.fonts.load(f)));
await document.fonts.ready;

const ctx = { THREE, scene, rig, overlay, T, fonts, photos, W, H, env };
const shots = [hookCity, stats, brand, modules, founders, finale].map((m) => m.build(ctx));

// ---------------------------------------------------------------- caméra globale : clés par canal, interpolées sans à-coups
const CAM = cameraKeys(T);
const ch = {
  x: pchip(CAM.map((k) => [k[0], k[1][0]])), y: pchip(CAM.map((k) => [k[0], k[1][1]])), z: pchip(CAM.map((k) => [k[0], k[1][2]])),
  az: pchip(CAM.map((k) => [k[0], k[2]])), el: pchip(CAM.map((k) => [k[0], k[3]])),
  h: pchip(CAM.map((k) => [k[0], Math.log(k[4])])), roll: pchip(CAM.map((k) => [k[0], k[5] || 0])),
};
function camAt(t) {
  const s = { target: [ch.x(t), ch.y(t), ch.z(t)], az: ch.az(t), el: ch.el(t), halfH: Math.exp(ch.h(t)), roll: ch.roll(t), shake: [0, 0] };
  for (const sh of shots) if (sh.camera) sh.camera(t, s);
  return s;
}

const _v = new THREE.Vector3();
function renderAt(t) {
  const e = env(t);
  skyMat.uniforms.uTop.value.copy(e.top);
  skyMat.uniforms.uBot.value.copy(e.bot);
  skyMat.uniforms.uGlow.value.copy(e.glow).multiplyScalar(0.35);
  skyMat.uniforms.uStars.value = e.stars;
  skyMat.uniforms.uTime.value = t;
  hemi.color.copy(e.hemiSky); hemi.groundColor.copy(e.hemiGround); hemi.intensity = e.hemiI;
  sun.color.copy(e.sun); sun.intensity = e.sunI;
  setNight(e.night);
  bloom.strength = e.bloom;
  bloom.threshold = THREE.MathUtils.lerp(1.9, 1.0, Math.max(e.night, seg(t, 4.6, 3.0)));
  bloom.radius = 0.55;

  for (const sh of shots) sh.update(t, e);

  // caméra + flou de bougé (obturateur à 180° : demi-image)
  const s = camAt(t);
  const prev = camAt(t - 0.5 / T.fps);
  rig.set(prev);
  const p = rig.project(s.target);
  rig.set(s);
  const dx = (p[0] - 960) / 1920, dy = -(p[1] - 540) / 1080;
  const zoom = Math.log(prev.halfH / s.halfH);
  const mag = Math.hypot(dx * 1920, dy * 1080);
  blur.enabled = mag > 2.0 || Math.abs(zoom) > 0.004;
  blur.uniforms.uDir.value.set(dx, dy);
  blur.uniforms.uZoom.value = zoom;

  // ombre portée : le soleil suit la cible de la caméra
  const el = THREE.MathUtils.degToRad(e.sunEl), saz = AZ - 0.9;
  _v.set(Math.cos(el) * Math.sin(saz), Math.sin(el), Math.cos(el) * Math.cos(saz));
  sun.target.position.set(...s.target);
  sun.position.set(s.target[0] + _v.x * 120, s.target[1] + _v.y * 120, s.target[2] + _v.z * 120);
  const ext = Math.max(18, s.halfH * (W / H) * 1.25);
  Object.assign(sun.shadow.camera, { left: -ext, right: ext, top: ext, bottom: -ext, near: 10, far: 320 });
  sun.shadow.camera.updateProjectionMatrix();

  for (const sh of shots) if (sh.overlay) sh.overlay(t, e);

  fin.uniforms.uTime.value = t;
  fin.uniforms.uFade.value = 0;
  fin.uniforms.uFlash.value = 0;
  for (const sh of shots) if (sh.post) sh.post(t, { fin, bloom });
  composer.render();
}

window.renderAt = renderAt;
window.__anchors = (t) => { renderAt(t); const out = {}; for (const [k, f] of Object.entries(ctx.anchors || {})) out[k] = rig.project(f()).map(Math.round); return out; };
window.__T = T;
window.__ready = true;
