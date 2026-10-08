// Disposition du monde : un archipel lu en isométrie (caméra au sud-est, azimut 45°).
// sp(x, y) place un point en « coordonnées écran au sol » : x vers la droite de l'image, y vers le haut.
export const AZ = Math.PI / 4;
export const RIGHT = [Math.cos(AZ), 0, -Math.sin(AZ)];
export const UP = [-Math.sin(AZ), 0, -Math.cos(AZ)];

export function sp(sx, sy, y = 0) {
  return [sx * RIGHT[0] + sy * UP[0], y, sx * RIGHT[2] + sy * UP[2]];
}

export const CITY = sp(0, 0);
export const STADIUM = sp(-36, 46);
export const MODULES = Array.from({ length: 7 }, (_, i) => sp(-12 + 15.5 * i, 66 + (i % 2 ? 2.6 : -1.4), i % 2 ? 1.2 : 0));
export const STREET = sp(64, 18);
export const MEDAL = sp(34.5, 83, 9);
