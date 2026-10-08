// Mouvements de caméra du film : [t, cible, azimut, élévation, demi-hauteur de vue, roulis]
import { ISO_EL } from './core/rig.js';
import { AZ, CITY, STADIUM, MODULES, STREET, sp } from './layout.js';

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];

export function cameraKeys(T) {
  const E = ISO_EL;
  return [
    [0.0, add(CITY, [0, 3.2, 0]), AZ + 0.34, E + 0.06, 3.0, 0],
    [1.0, add(CITY, [0, 0.8, 0]), AZ + 0.28, E + 0.05, 2.8, 0],
    [2.6, add(CITY, [0, 0.0, 0]), AZ + 0.18, E + 0.03, 9.0, 0],
    [5.4, add(CITY, [0, -1.2, 0]), AZ + 0.05, E + 0.02, 16.5, 0],
    [9.4, add(sp(-10.5, 0.8), [0, 1.5, 0]), AZ - 0.06, E, 15.0, 0],
    [11.5, add(sp(-9.5, 1.0), [0, 1.8, 0]), AZ - 0.12, E, 14.4, 0],
    [12.9, add(sp(0.8, 2.2), [0, 4.2, 0]), AZ - 0.2, E + 0.05, 12.0, 0],
    [19.6, add(sp(0.4, 1.8), [0, 4.0, 0]), AZ - 0.34, E + 0.04, 12.6, 0],
    [21.0, add(CITY, [0, 5.0, 0]), AZ - 0.3, E + 0.07, 14.5, 0],
    [21.9, add(CITY, [0, 5.5, 0]), AZ - 0.27, E + 0.08, 15.0, 0],
    [22.0, add(CITY, [0, 5.6, 0]), AZ - 0.26, E + 0.08, 15.0, 0],
    [23.05, add(STADIUM, [0, 3.2, 0]), AZ - 0.1, E + 0.03, 12.0, 0],
    [24.0, add(STADIUM, [0, 3.2, 0]), AZ - 0.06, E + 0.03, 11.2, 0],
    [24.9, add(STADIUM, [0, 4.4, 0.4]), AZ - 0.02, E + 0.01, 7.6, 0],
    [27.55, add(STADIUM, [0, 4.2, 0.4]), AZ + 0.06, E + 0.0, 8.6, 0],
    ...moduleKeys(T, E),
    [43.3, sp(34.5, 72, 5.0), AZ, E + 0.02, 27.0, 0],
    [45.6, sp(34.5, 73, 5.0), AZ + 0.03, E + 0.02, 28.0, 0],
    [46.7, add(STREET, [-10.0, 5.6, 3.0]), AZ - 0.12, E - 0.02, 10.0, 0],
    [47.7, add(add(STREET, [-11.2, 4.3, 3.2]), sp(-3.0, 0)), AZ - 0.1, E - 0.03, 8.2, 0],
    [52.6, add(add(STREET, [11.2, 4.3, 3.2]), sp(-3.0, 0)), AZ + 0.02, E - 0.03, 8.2, 0],
    [54.6, add(STREET, [0.5, 5.0, 1.5]), AZ + 0.05, E - 0.01, 13.8, 0],
    [55.7, add(STREET, [0.5, 5.2, 1.5]), AZ + 0.07, E, 14.4, 0],
    [58.6, sp(16, 36, 2.0), AZ + 0.02, E + 0.06, 50.0, 0],
    [62.0, sp(16, 37, 2.0), AZ + 0.05, E + 0.06, 52.0, 0],
  ];
}

function moduleKeys(T, E) {
  const keys = [];
  MODULES.forEach((p, i) => {
    const t0 = T.modules.start + i * T.modules.step;
    const frame = (dx) => add(add(p, sp(-2.4 + dx, 0.6)), [0, 2.4, 0]);
    keys.push([t0, frame(0), AZ - 0.04 + i * 0.01, E + 0.03, 7.4, 0]);
    keys.push([t0 + T.modules.step - 0.45, frame(0.55), AZ - 0.02 + i * 0.01, E + 0.03, 7.1, 0]);
  });
  return keys;
}
