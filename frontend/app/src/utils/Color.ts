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

export function randomColor(): string {
  return Math.floor(Math.random() * 16777215)
    .toString(16)
    .padStart(6, '0')
    .toUpperCase();
}
