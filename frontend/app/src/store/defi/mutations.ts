import { MutationTree } from 'vuex';
import { Watcher, WatcherTypes } from '@/services/defi/types';
import { defaultState, DefiState } from '@/store/defi/state';
import {
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  MakerDAOVaultDetails
} from '@/store/defi/types';

export const mutations: MutationTree<DefiState> = {
  dsrHistory(state: DefiState, history: DSRHistory) {
    state.dsrHistory = history;
  },
  dsrBalances(state: DefiState, balances: DSRBalances) {
    state.dsrBalances = balances;
  },
  watchers(state: DefiState, watchers: Watcher<WatcherTypes>[]) {
    state.watchers = watchers;
  },
  makerDAOVaults(state: DefiState, makerDAOVaults: MakerDAOVault[]) {
    state.makerDAOVaults = makerDAOVaults;
  },
  makerDAOVaultDetails(
    state: DefiState,
    makerDAOVaultDetails: MakerDAOVaultDetails[]
  ) {
    state.makerDAOVaultDetails = makerDAOVaultDetails;
  },
  reset(state: DefiState) {
    Object.assign(state, defaultState());
  }
};
