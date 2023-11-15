import { AddressNamePriority } from '@/types/settings/address-name-priorities';
import { PriceOracle } from '@/types/settings/price-oracle';
import { type PrioritizedListItemData } from '@/types/settings/prioritized-list-data';

export const EmptyListId = 'empty_list_id';

export type PrioritizedListId =
  | AddressNamePriority
  | PriceOracle
  | typeof EmptyListId;

export const BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.BLOCKCHAIN_ACCOUNT
  };

export const ENS_NAMES_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.ENS_NAMES
  };

export const ETHEREUM_TOKENS_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.ETHEREUM_TOKENS
  };

export const GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.GLOBAL_ADDRESSBOOK
  };

export const HARDCODED_MAPPINGS_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.HARDCODED_MAPPINGS
  };

export const PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: AddressNamePriority.PRIVATE_ADDRESSBOOK
  };

export const CRYPTOCOMPARE_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.CRYPTOCOMPARE,
    icon: './assets/images/oracles/cryptocompare.png'
  };

export const COINGECKO_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.COINGECKO,
    icon: './assets/images/oracles/coingecko.svg'
  };

export const DEFILAMA_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.DEFILLAMA,
    icon: './assets/images/oracles/defillama.svg'
  };

export const UNISWAP2_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.UNISWAP2,
    icon: './assets/images/protocols/uniswap.svg'
  };

export const UNISWAP3_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.UNISWAP3,
    icon: './assets/images/protocols/uniswap.svg'
  };

export const MANUALCURRENT_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.MANUALCURRENT,
    icon: './assets/images/oracles/book.svg'
  };

export const MANUAL_PRIO_LIST_ITEM: PrioritizedListItemData<PrioritizedListId> =
  {
    identifier: PriceOracle.MANUAL,
    icon: './assets/images/oracles/book.svg'
  };
