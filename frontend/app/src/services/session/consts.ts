import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';

export enum Module {
  YEARN = 'yearn_vaults',
  YEARN_V2 = 'yearn_vaults_v2',
  COMPOUND = 'compound',
  MAKERDAO_VAULTS = 'makerdao_vaults',
  MAKERDAO_DSR = 'makerdao_dsr',
  AAVE = 'aave',
  UNISWAP = 'uniswap',
  BALANCER = 'balancer',
  ADEX = 'adex',
  LOOPRING = 'loopring',
  ETH2 = 'eth2',
  SUSHISWAP = 'sushiswap',
  NFTS = 'nfts',
  PICKLE = 'pickle_finance',
  LIQUITY = 'liquity'
}

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
