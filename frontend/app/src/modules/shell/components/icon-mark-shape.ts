/** How far in from each edge the samples are taken, as a fraction of the side. */
const EDGE_INSET = 0.06;

/** Alpha above which a sample counts as painted. */
const OPAQUE_ALPHA = 200;

const SAMPLE_SIZE = 32;

const shapes = new Map<string, boolean>();

/**
 * Whether a loaded logo fills the circle it is framed in by itself: a full-bleed square (Kusama,
 * Base) or a logo that brings its own disc (most token logos). Either paints the middle of all four
 * edges; a glyph on a transparent ground (Aave's arc, Ethereum's diamond) does not.
 *
 * A filling logo is cropped to the circle and reads as a disc in its own colours. Given the backing
 * and inset meant for glyphs it shows a ring of backing around its own disc instead.
 *
 * Reads pixels, so it needs a same-origin or CORS-enabled image; a tainted canvas throws, which
 * answers `false` and keeps the backing.
 */
export function fillsFrame(image: HTMLImageElement): boolean {
  const key = image.currentSrc || image.src;
  const known = shapes.get(key);
  if (known !== undefined)
    return known;

  let result = false;
  try {
    const canvas = document.createElement('canvas');
    canvas.width = SAMPLE_SIZE;
    canvas.height = SAMPLE_SIZE;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (context) {
      context.drawImage(image, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE);
      const near = Math.round(SAMPLE_SIZE * EDGE_INSET);
      const far = SAMPLE_SIZE - 1 - near;
      const middle = Math.floor(SAMPLE_SIZE / 2);
      const edges: [number, number][] = [[middle, near], [middle, far], [near, middle], [far, middle]];
      result = edges.every(([x, y]) => (context.getImageData(x, y, 1, 1).data[3] ?? 0) > OPAQUE_ALPHA);
    }
  }
  catch {
    result = false;
  }

  shapes.set(key, result);
  return result;
}
