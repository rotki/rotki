import { z } from 'zod';

export const PriceOracle = {
  ALCHEMY: 'alchemy',
  BLOCKCHAIN: 'blockchain',
  COINGECKO: 'coingecko',
  COINBASE: 'coinbase',
  CRYPTOCOMPARE: 'cryptocompare',
  DEFILLAMA: 'defillama',
  FIAT: 'fiat',
  KRAKEN: 'kraken',
  MANUAL: 'manual',
  MANUALCURRENT: 'manualcurrent',
  MORALIS: 'moralis',
  UNISWAP2: 'uniswapv2',
  UNISWAP3: 'uniswapv3',
} as const;

export type PriceOracle = typeof PriceOracle[keyof typeof PriceOracle];

export const PriceOracleEnum = z.enum(PriceOracle);
