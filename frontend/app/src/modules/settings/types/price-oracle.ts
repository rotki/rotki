import { z } from 'zod/v4';

export const PriceOracle = {
  ALCHEMY: 'alchemy',
  BLOCKCHAIN: 'blockchain',
  COINGECKO: 'coingecko',
  CRYPTOCOMPARE: 'cryptocompare',
  DEFILLAMA: 'defillama',
  FIAT: 'fiat',
  MANUAL: 'manual',
  MANUALCURRENT: 'manualcurrent',
  UNISWAP2: 'uniswapv2',
  UNISWAP3: 'uniswapv3',
} as const;

export type PriceOracle = typeof PriceOracle[keyof typeof PriceOracle];

export const PriceOracleEnum = z.enum(PriceOracle);
