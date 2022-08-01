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
  allProtocols: {},
  compoundBalances: {},
  compoundHistory: defaultCompoundHistory(),
  airdrops: {}
});

export const state: DefiState = defaultState();
