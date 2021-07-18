import { EXTERNAL_EXCHANGES, SUPPORTED_EXCHANGES } from '@/data/defaults';

export const MODULE_YEARN = 'yearn_vaults';
export const MODULE_YEARN_V2 = 'yearn_vaults_v2';
export const MODULE_COMPOUND = 'compound';
export const MODULE_MAKERDAO_VAULTS = 'makerdao_vaults';
export const MODULE_MAKERDAO_DSR = 'makerdao_dsr';
export const MODULE_AAVE = 'aave';
export const MODULE_UNISWAP = 'uniswap';
export const MODULE_BALANCER = 'balancer';
export const MODULE_ADEX = 'adex';
export const MODULE_LOOPRING = 'loopring';
export const MODULE_ETH2 = 'eth2';

export const MODULES = [
  MODULE_AAVE,
  MODULE_MAKERDAO_DSR,
  MODULE_MAKERDAO_VAULTS,
  MODULE_COMPOUND,
  MODULE_YEARN,
  MODULE_YEARN_V2,
  MODULE_UNISWAP,
  MODULE_BALANCER,
  MODULE_ADEX,
  MODULE_LOOPRING,
  MODULE_ETH2
] as const;

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
  ...MODULES
];
