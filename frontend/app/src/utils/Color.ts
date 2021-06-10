import { assert } from '@/utils/assertions';

export function invertColor(color: string, bw: boolean = true) {
  if (color.indexOf('#') === 0) {
    color = color.slice(1);
  }

  if (color.length === 3) {
    color = color[0] + color[0] + color[1] + color[1] + color[2] + color[2];
  }

  assert(color.length === 6, `Invalid color: ${color}`);

  const r = parseInt(color.slice(0, 2), 16);
  const g = parseInt(color.slice(2, 4), 16);
  const b = parseInt(color.slice(4, 6), 16);

  if (bw) {
    return r * 0.299 + g * 0.587 + b * 0.114 > 186 ? '000000' : 'FFFFFF';
  }

  const rInv = (255 - r).toString(16).padStart(2, '0');
  const gInv = (255 - g).toString(16).padStart(2, '0');
  const bInv = (255 - b).toString(16).padStart(2, '0');

  return `${rInv}${gInv}${bInv}`;
}

const randomInt = (min: number, max: number): number => {
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

function toHex(value: number): string {
  return Math.round(value * 255)
    .toString(16)
    .padStart(2, '0')
    .toUpperCase();
}

function hslToRgb(h: number, s: number, l: number): string {
  let r: number, g: number, b: number;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = function hue2rgb(p: number, q: number, t: number) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  return `${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export function randomColor(): string {
  const h = randomInt(0, 360);
  const s = randomInt(42, 98);
  const l = randomInt(40, 90);
  return hslToRgb((1 / 360) * h, s / 100, l / 100);
}
