import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';
import { Module } from '@/types/modules';

export const ALL_CENTRALIZED_EXCHANGES = 'all_exchanges';
export const ALL_DECENTRALIZED_EXCHANGES = 'all_decentralized_exchanges';
export const ALL_MODULES = 'all_modules';
export const ALL_TRANSACTIONS = 'ethereum_transactions';
export const PURGABLE = [
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  ...SUPPORTED_EXCHANGES,
  ...EXTERNAL_EXCHANGES,
  ...Object.values(Module)
];
