import type { PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import { AddressNamePriority } from '@/types/settings/address-name-priorities';
import { PriceOracle } from '@/types/settings/price-oracle';

export const EmptyListId = 'empty_list_id';

export type PrioritizedListId = AddressNamePriority | PriceOracle | typeof EmptyListId;

export const BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.BLOCKCHAIN_ACCOUNT,
};

export const ENS_NAMES_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.ENS_NAMES,
};

export const ETHEREUM_TOKENS_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.ETHEREUM_TOKENS,
};

export const GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.GLOBAL_ADDRESSBOOK,
};

export const HARDCODED_MAPPINGS_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.HARDCODED_MAPPINGS,
};

export const PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData<AddressNamePriority> = {
  identifier: AddressNamePriority.PRIVATE_ADDRESSBOOK,
};

export const CRYPTOCOMPARE_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/services/cryptocompare.svg',
  identifier: PriceOracle.CRYPTOCOMPARE,
};

export const COINGECKO_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/services/coingecko.svg',
  identifier: PriceOracle.COINGECKO,
};

export const DEFILAMA_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/services/defillama.svg',
  identifier: PriceOracle.DEFILLAMA,
};

export const ALCHEMY_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/services/alchemy.svg',
  identifier: PriceOracle.ALCHEMY,
};

export const UNISWAP2_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/protocols/uniswap.svg',
  identifier: PriceOracle.UNISWAP2,
};

export const UNISWAP3_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/protocols/uniswap.svg',
  identifier: PriceOracle.UNISWAP3,
};

export const YAHOOFINANCE_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/services/yahoofinance.svg',
  identifier: PriceOracle.YAHOOFINANCE,
};

export const MANUAL_PRIO_LIST_ITEM: PrioritizedListItemData<PriceOracle> = {
  icon: './assets/images/oracles/book.svg',
  identifier: PriceOracle.MANUAL,
};
