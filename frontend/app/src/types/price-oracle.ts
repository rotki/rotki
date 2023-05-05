import { z } from 'zod';

export enum PriceOracle {
  BLOCKCHAIN = 'blockchain',
  COINGECKO = 'coingecko',
  CRYPTOCOMPARE = 'cryptocompare',
  FIAT = 'fiat',
  MANUAL = 'manual',
  MANUALCURRENT = 'manualcurrent',
  SADDLE = 'saddle',
  UNISWAP2 = 'uniswapv2',
  UNISWAP3 = 'uniswapv3',
  DEFILLAMA = 'defillama'
}

export const PriceOracleEnum = z.nativeEnum(PriceOracle);
