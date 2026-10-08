// Post-production : bloom, flou de bougé directionnel, tone mapping, SMAA, étalonnage final (vignette, grain).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';

const MotionBlurShader = {
  uniforms: { tDiffuse: { value: null }, uDir: { value: new THREE.Vector2() }, uZoom: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform vec2 uDir; uniform float uZoom; varying vec2 vUv;
    void main(){
      vec4 acc = vec4(0.0);
      vec2 rad = (vUv - 0.5) * uZoom;
      for (int i = 0; i < 16; i++) {
        float k = (float(i) / 15.0) - 0.5;
        acc += texture2D(tDiffuse, vUv + uDir * k + rad * k);
      }
      gl_FragColor = acc / 16.0;
    }`,
};

const FinalShader = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uVignette: { value: 0.28 }, uGrain: { value: 0.012 },
    uCA: { value: 0.0012 }, uFade: { value: 0 }, uFlash: { value: 0 }, uRes: { value: new THREE.Vector2(1920, 1080) },
    uLift: { value: new THREE.Color(0, 0, 0) },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime, uVignette, uGrain, uCA, uFade, uFlash; uniform vec2 uRes; uniform vec3 uLift;
    varying vec2 vUv;
    float hash(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
    void main(){
      vec2 d = vUv - 0.5;
      float r = texture2D(tDiffuse, vUv + d * uCA).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv - d * uCA).b;
      vec3 c = vec3(r, g, b);
      c += uLift;
      float v = 1.0 - uVignette * smoothstep(0.25, 0.95, length(d * vec2(1.0, 0.82)) * 1.35);
      c *= v;
      float n = hash(vUv * uRes + fract(uTime * 7.31) * 113.0) - 0.5;
      c += n * uGrain * (0.6 + 0.4 * (1.0 - dot(c, vec3(0.33))));
      c = mix(c, vec3(1.0, 0.97, 0.92), uFlash);
      c *= (1.0 - uFade);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export function makeComposer(renderer, scene, camera, W, H) {
  const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType });
  const composer = new EffectComposer(renderer, rt);
  composer.setPixelRatio(1);
  composer.setSize(W, H);
  const render = new RenderPass(scene, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.45, 0.55, 0.92);
  const blur = new ShaderPass(MotionBlurShader);
  blur.enabled = false;
  const out = new OutputPass();
  const smaa = new SMAAPass(W, H);
  const fin = new ShaderPass(FinalShader);
  fin.uniforms.uRes.value.set(W, H);
  composer.addPass(render);
  composer.addPass(bloom);
  composer.addPass(blur);
  composer.addPass(out);
  composer.addPass(smaa);
  composer.addPass(fin);
  return { composer, bloom, blur, fin };
}
