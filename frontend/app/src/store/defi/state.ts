import { Watcher, WatcherTypes } from '@/services/defi/types';
import {
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  MakerDAOVaultDetails
} from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

export interface DefiState {
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
  makerDAOVaults: MakerDAOVault[];
  makerDAOVaultDetails: MakerDAOVaultDetails[];
  watchers: Watcher<WatcherTypes>[];
}

export const defaultState = (): DefiState => ({
  dsrHistory: {},
  dsrBalances: {
    currentDSR: Zero,
    balances: {}
  },
  makerDAOVaults: [],
  makerDAOVaultDetails: [],
  watchers: []
});

export const state: DefiState = defaultState();
