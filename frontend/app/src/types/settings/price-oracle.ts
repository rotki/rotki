import { z } from 'zod';

export enum PriceOracle {
  BLOCKCHAIN = 'blockchain',
  COINGECKO = 'coingecko',
  CRYPTOCOMPARE = 'cryptocompare',
  FIAT = 'fiat',
  MANUALCURRENT = 'manualcurrent',
  UNISWAP2 = 'uniswapv2',
  UNISWAP3 = 'uniswapv3',
  DEFILLAMA = 'defillama',
  ALCHEMY = 'alchemy',
}

export const PriceOracleEnum = z.nativeEnum(PriceOracle);
