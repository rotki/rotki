import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fillsFrame } from '@/modules/shell/components/icon-mark-shape';

/** The four samples on a 32px canvas: the middle of each edge, 2px in. */
const EDGES = ['16,2', '16,29', '2,16', '29,16'];

const originalGetContext = Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype, 'getContext');

let alphaAt: (x: number, y: number) => number;
let context: { drawImage: ReturnType<typeof vi.fn>; getImageData: ReturnType<typeof vi.fn> } | null;
let imageCount = 0;

/** A fresh source each time: answers are cached per source for the whole module. */
function image(): HTMLImageElement {
  const element = new Image();
  element.src = `https://example.com/logo-${++imageCount}.png`;
  return element;
}

/** Paints the given edge samples at full alpha and leaves everything else transparent. */
function paint(...edges: string[]): void {
  alphaAt = (x, y): number => (edges.includes(`${x},${y}`) ? 255 : 0);
}

describe('fillsFrame', () => {
  beforeEach(() => {
    paint();
    context = {
      drawImage: vi.fn(),
      getImageData: vi.fn((x: number, y: number) => ({ data: new Uint8ClampedArray([0, 0, 0, alphaAt(x, y)]) })),
    };
    // happy-dom has no canvas backend, so the 2d context is stood in for.
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: () => context,
    });
  });

  afterEach(() => {
    if (originalGetContext)
      Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', originalGetContext);
  });

  it('should answer true for a logo that paints the middle of all four edges', () => {
    paint(...EDGES);

    expect(fillsFrame(image())).toBe(true);
  });

  it('should answer false for a glyph that leaves an edge transparent', () => {
    paint(...EDGES.slice(1));

    expect(fillsFrame(image())).toBe(false);
  });

  it('should not count a half-transparent edge as painted', () => {
    alphaAt = (): number => 200;

    expect(fillsFrame(image())).toBe(false);

    alphaAt = (): number => 201;

    expect(fillsFrame(image())).toBe(true);
  });

  it('should answer false without a 2d context', () => {
    context = null;

    expect(fillsFrame(image())).toBe(false);
  });

  it('should answer false when the canvas is tainted and reading pixels throws', () => {
    paint(...EDGES);
    context?.getImageData.mockImplementation(() => {
      throw new DOMException('The canvas has been tainted', 'SecurityError');
    });

    expect(fillsFrame(image())).toBe(false);
  });

  it('should read each source once and answer from the cache after', () => {
    paint(...EDGES);
    const logo = image();

    expect(fillsFrame(logo)).toBe(true);

    paint();
    expect(fillsFrame(logo)).toBe(true);
    expect(context?.drawImage).toHaveBeenCalledOnce();
  });
});
