import type { PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import {
  ALCHEMY_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  COINBASE_PRIO_LIST_ITEM,
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  KRAKEN_PRIO_LIST_ITEM,
  MORALIS_PRIO_LIST_ITEM,
  type PrioritizedListId,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';

/**
 * Oracles offered in the historic prices prioritized list. Every entry must be a valid
 * backend `HistoricalPriceOracle` member, otherwise saving the setting is rejected.
 * Kept in sync with the backend via price-oracle-lists.spec.ts.
 */
export const HISTORICAL_PRICE_ORACLE_ITEMS: Array<PrioritizedListItemData<PrioritizedListId>> = [
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  COINBASE_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  ALCHEMY_PRIO_LIST_ITEM,
  MORALIS_PRIO_LIST_ITEM,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
];

/**
 * Oracles offered in the latest prices prioritized list. Must match the backend
 * `SETTABLE_CURRENT_PRICE_ORACLES` set, otherwise saving the setting is rejected.
 * Kept in sync with the backend via price-oracle-lists.spec.ts.
 */
export const CURRENT_PRICE_ORACLE_ITEMS: Array<PrioritizedListItemData<PrioritizedListId>> = [
  CRYPTOCOMPARE_PRIO_LIST_ITEM,
  COINGECKO_PRIO_LIST_ITEM,
  DEFILAMA_PRIO_LIST_ITEM,
  ALCHEMY_PRIO_LIST_ITEM,
  MORALIS_PRIO_LIST_ITEM,
  UNISWAP2_PRIO_LIST_ITEM,
  UNISWAP3_PRIO_LIST_ITEM,
  KRAKEN_PRIO_LIST_ITEM,
];
