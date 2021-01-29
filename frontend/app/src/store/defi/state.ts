import { DefiState } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

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
  compoundHistory: {
    events: [],
    debtLoss: {},
    interestProfit: {},
    rewards: {},
    liquidationProfit: {}
  },
  yearnVaultsHistory: {},
  yearnVaultsBalances: {},
  uniswapBalances: {},
  uniswapTrades: {},
  uniswapEvents: {},
  airdrops: {}
});

export const state: DefiState = defaultState();
