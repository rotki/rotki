import { CompoundHistory } from '@/services/defi/types/compound';
import { DefiState } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

export const defaultCompoundHistory = (): CompoundHistory => ({
  events: [],
  debtLoss: {},
  interestProfit: {},
  rewards: {},
  liquidationProfit: {}
});

export const defaultState = (): DefiState => ({
  dsrHistory: {},
  dsrBalances: {
    currentDsr: Zero,
    balances: {}
  },
  makerDAOVaults: [],
  makerDAOVaultDetails: [],
  aaveBalances: {},
  aaveHistory: {},
  allProtocols: {},
  compoundBalances: {},
  compoundHistory: defaultCompoundHistory(),
  yearnVaultsBalances: {},
  yearnVaultsHistory: {},
  yearnVaultsV2Balances: {},
  yearnVaultsV2History: {},
  airdrops: {},
  balancerBalances: {},
  balancerTrades: {},
  balancerEvents: {}
});

export const state: DefiState = defaultState();
