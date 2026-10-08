// Texte 3D extrudé (polices TTF chargées et converties par three.js).
import * as THREE from 'three';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

export async function loadFont(url) {
  const json = await new Promise((res, rej) => new TTFLoader().load(url, res, undefined, rej));
  return new Font(json);
}

/** Une géométrie par lettre + avance horizontale, pour animer chaque caractère. */
export function letterGeos(font, text, { size = 1, depth = 0.3, bevel = 0.03, curve = 6 } = {}) {
  const scale = size / font.data.resolution;
  const out = [];
  let x = 0;
  for (const ch of text) {
    const glyph = font.data.glyphs[ch] || font.data.glyphs['?'];
    const adv = (glyph ? glyph.ha : font.data.resolution * 0.5) * scale;
    if (ch !== ' ') {
      const g = new TextGeometry(ch, {
        font, size, depth, curveSegments: curve,
        bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 2,
      });
      g.computeBoundingBox();
      out.push({ ch, geo: g, x, adv });
    }
    x += adv;
  }
  return { letters: out, width: x };
}

/** Bloc de texte centré (une seule géométrie). */
export function textMesh(font, text, materials, opts = {}) {
  const g = new TextGeometry(text, {
    font, size: opts.size ?? 1, depth: opts.depth ?? 0.3, curveSegments: opts.curve ?? 6,
    bevelEnabled: (opts.bevel ?? 0.03) > 0, bevelThickness: opts.bevel ?? 0.03, bevelSize: (opts.bevel ?? 0.03) * 0.8, bevelSegments: 2,
  });
  g.computeBoundingBox();
  const bb = g.boundingBox;
  g.translate(-(bb.max.x + bb.min.x) / 2, -(bb.max.y + bb.min.y) / 2, -(bb.max.z + bb.min.z) / 2);
  const m = new THREE.Mesh(g, materials);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}
