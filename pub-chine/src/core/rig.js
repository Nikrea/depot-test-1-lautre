// Caméra isométrique (orthographique) pilotée par : cible, azimut, élévation, demi-hauteur de vue, roulis.
import * as THREE from 'three';

export const ISO_EL = Math.atan(1 / Math.SQRT2); // 35.264° : isométrie vraie

export class Rig {
  constructor(W, H) {
    this.W = W; this.H = H;
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 2000);
    this.state = null;
    this._v = new THREE.Vector3();
  }

  /** s = { target:[x,y,z], az, el, halfH, roll, shake:[sx,sy] } */
  set(s) {
    const { cam } = this;
    const [tx, ty, tz] = s.target;
    const ce = Math.cos(s.el), se = Math.sin(s.el);
    const D = 600;
    cam.position.set(tx + D * ce * Math.sin(s.az), ty + D * se, tz + D * ce * Math.cos(s.az));
    cam.up.set(0, 1, 0);
    cam.lookAt(tx, ty, tz);
    if (s.roll) cam.rotateZ(s.roll);
    if (s.shake && (s.shake[0] || s.shake[1])) {
      cam.translateX(s.shake[0] * s.halfH);
      cam.translateY(s.shake[1] * s.halfH);
    }
    const asp = this.W / this.H;
    cam.left = -s.halfH * asp; cam.right = s.halfH * asp;
    cam.top = s.halfH; cam.bottom = -s.halfH;
    cam.near = 1; cam.far = 1400;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld(true);
    this.state = s;
  }

  /** Projette un point monde en pixels du calque typographique (repère 1920 x 1080). */
  project(p) {
    const v = this._v.set(p[0], p[1], p[2]).project(this.cam);
    return [(v.x * 0.5 + 0.5) * 1920, (-v.y * 0.5 + 0.5) * 1080];
  }

  /** Taille à l'écran (px) d'une longueur monde. */
  px(len) {
    return (len / (2 * this.state.halfH)) * this.H;
  }
}
