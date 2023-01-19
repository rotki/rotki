// Source: https://github.com/ethereum/blockies
// The random number is a js implementation of the Xorshift PRNG
interface BlockieOptions {
  /** seed used to generate icon data, default: random */
  seed: string;
  /** to manually specify the icon color, default: random */
  color: string;
  /** choose a different background color, default: random */
  bgcolor: string;
  /** width/height of the icon in blocks, default: 8 */
  size: number;
  /** width/height of each block in pixels, default: 4 */
  scale: number;
  /**
   * each pixel has a 13% chance of being of a third color, default: random.
   *
   * Set to -1 to disable it.
   *
   * These "spots" create structures that look like eyes, mouths and noses.
   */
  spotColor: string;
}

const randSeed = new Array(4); // Xorshift: [x, y, z, w] 32 bit values

const seedRand = (seed: string) => {
  for (let i = 0; i < randSeed.length; i++) {
    randSeed[i] = 0;
  }
  for (let i = 0; i < seed.length; i++) {
    randSeed[i % 4] =
      (randSeed[i % 4] << 5) - randSeed[i % 4] + seed.charCodeAt(i);
  }
};

const rand = () => {
  // based on Java's String.hashCode(), expanded to 4 32bit values
  const t = randSeed[0] ^ (randSeed[0] << 11);

  randSeed[0] = randSeed[1];
  randSeed[1] = randSeed[2];
  randSeed[2] = randSeed[3];
  randSeed[3] = randSeed[3] ^ (randSeed[3] >> 19) ^ t ^ (t >> 8);

  return (randSeed[3] >>> 0) / ((1 << 31) >>> 0);
};

const createColor = () => {
  //saturation is the whole color spectrum
  const h = Math.floor(rand() * 360);
  //saturation goes from 40 to 100, it avoids greyish colors
  const s = `${rand() * 60 + 40}%`;
  //lightness can be anything from 0 to 100, but probabilities are a bell curve around 50%
  const l = `${(rand() + rand() + rand() + rand()) * 25}%`;

  return `hsl(${h},${s},${l})`;
};

const createImageData = (size: number) => {
  const width = size; // Only support square icons for now
  const height = size;

  const dataWidth = Math.ceil(width / 2);
  const mirrorWidth = width - dataWidth;

  const data = [];
  for (let y = 0; y < height; y++) {
    let row = [];
    for (let x = 0; x < dataWidth; x++) {
      // this makes foreground and background color to have a 43% (1/2.3) probability
      // spot color has 13% chance
      row[x] = Math.floor(rand() * 2.3);
    }
    const r = row.slice(0, mirrorWidth);
    r.reverse();
    row = row.concat(r);

    for (const element of row) {
      data.push(element);
    }
  }

  return data;
};

const buildOpts = (opts: Partial<BlockieOptions>): BlockieOptions => {
  const newOpts: Partial<BlockieOptions> = {};

  newOpts.seed = opts.seed || Math.floor(Math.random() * 10 ** 16).toString(16);

  seedRand(newOpts.seed);

  // eslint-disable-next-line unicorn/explicit-length-check
  newOpts.size = opts.size || 8;
  newOpts.scale = opts.scale || 4;
  newOpts.color = opts.color || createColor();
  newOpts.bgcolor = opts.bgcolor || createColor();
  newOpts.spotColor = opts.spotColor || createColor();

  return newOpts as BlockieOptions;
};

const renderIcon = (
  opts: Partial<BlockieOptions>,
  canvas: HTMLCanvasElement
) => {
  const newOpts: BlockieOptions = buildOpts(opts || {});
  const imageData = createImageData(newOpts.size);
  const width = Math.sqrt(imageData.length);

  canvas.width = canvas.height = newOpts.size * newOpts.scale;

  const cc = canvas.getContext('2d') as CanvasRenderingContext2D;
  if (cc) {
    cc.fillStyle = newOpts.bgcolor;
    cc.fillRect(0, 0, canvas.width, canvas.height);
    cc.fillStyle = newOpts.color;

    for (const [i, imageDatum] of imageData.entries()) {
      // if data is 0, leave the background
      if (imageDatum) {
        const row = Math.floor(i / width);
        const col = i % width;

        // if data is 2, choose spot color, if 1 choose foreground
        cc.fillStyle = imageDatum === 1 ? newOpts.color : newOpts.spotColor;

        cc.fillRect(
          col * newOpts.scale,
          row * newOpts.scale,
          newOpts.scale,
          newOpts.scale
        );
      }
    }
  }

  return canvas;
};

export const createBlockie = (opts: Partial<BlockieOptions>): string => {
  const canvas = document.createElement('canvas');

  renderIcon(opts, canvas);

  return canvas.toDataURL('image/jpeg');
};
