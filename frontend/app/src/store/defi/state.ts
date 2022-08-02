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
  allProtocols: {},
  airdrops: {}
});

export const state: DefiState = defaultState();
