import { z } from 'zod';

export const PriceOracle = z.enum([
  'cryptocompare',
  'coingecko',
  'manual',
  'uniswapv3',
  'uniswapv2',
  'saddle',
  'manualcurrent'
]);
export type PriceOracle = z.infer<typeof PriceOracle>;
