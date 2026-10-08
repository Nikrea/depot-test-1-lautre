// Calque typographique DOM (net, piloté image par image — aucune transition CSS).
export class Overlay {
  constructor(root) {
    this.root = root;
    this.items = new Map();
  }

  add(id, html, cls = '') {
    const el = document.createElement('div');
    el.className = 'ov ' + cls;
    el.innerHTML = html;
    el.style.opacity = '0';
    this.root.appendChild(el);
    this.items.set(id, el);
    return el;
  }

  get(id) {
    return this.items.get(id);
  }

  /** Coupe un texte en lettres (spans) pour les animer une par une. */
  static letters(text, cls = 'ch') {
    return [...text].map((c) => `<span class="${cls}">${c === ' ' ? '&nbsp;' : c}</span>`).join('');
  }

  static words(text, cls = 'wd') {
    return text.split(' ').map((w) => `<span class="${cls}"><span class="wi">${w}</span></span>`).join(' ');
  }
}

/** Applique un état visuel à un élément. */
export function style(el, { x = 0, y = 0, o = 1, s = 1, sx = null, sy = null, r = 0, blur = 0, clip = null, skew = 0, origin = null } = {}) {
  if (!el) return;
  el.style.opacity = o <= 0.001 ? '0' : String(o);
  el.style.visibility = o <= 0.001 ? 'hidden' : 'visible';
  const scx = sx ?? s, scy = sy ?? s;
  el.style.transform = `translate(${x}px, ${y}px) rotate(${r}deg) skewX(${skew}deg) scale(${scx}, ${scy})`;
  if (origin) el.style.transformOrigin = origin;
  el.style.filter = blur > 0.05 ? `blur(${blur}px)` : 'none';
  if (clip !== null) el.style.clipPath = clip;
}
