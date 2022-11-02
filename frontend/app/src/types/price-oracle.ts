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

export const CRYPTOCOMPARE_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.CRYPTOCOMPARE,
  icon: '/assets/images/oracles/cryptocompare.png'
};

export const COINGECKO_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.COINGECKO,
  icon: '/assets/images/oracles/coingecko.svg'
};

export const UNISWAP2_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.UNISWAP2,
  icon: '/assets/images/defi/uniswap.svg'
};

export const UNISWAP3_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.UNISWAP3,
  icon: '/assets/images/defi/uniswap.svg'
};

export const SADDLE_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.SADDLE,
  icon: '/assets/images/airdrops/saddle-finance.svg'
};

export const MANUALCURRENT_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.MANUALCURRENT,
  icon: '/assets/images/oracles/book.svg'
};

export const MANUAL_PRIO_LIST_ITEM: PrioritizedListItemData = {
  identifier: PriceOracle.MANUAL,
  icon: '/assets/images/oracles/book.svg',
  extraDisplaySize: '40px'
};
