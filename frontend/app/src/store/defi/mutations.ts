import { MutationTree } from 'vuex';
import { Status } from '@/store/const';
import { defaultState } from '@/store/defi/state';
import {
  AaveBalances,
  AaveHistory,
  AllDefiProtocols,
  DefiState,
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
  makerDAOVaults(state: DefiState, makerDAOVaults: MakerDAOVault[]) {
    state.makerDAOVaults = makerDAOVaults;
  },
  makerDAOVaultDetails(
    state: DefiState,
    makerDAOVaultDetails: MakerDAOVaultDetails[]
  ) {
    state.makerDAOVaultDetails = makerDAOVaultDetails;
  },
  aaveBalances(state: DefiState, aaveBalances: AaveBalances) {
    state.aaveBalances = aaveBalances;
  },
  aaveHistory(state: DefiState, aaveHistory: AaveHistory) {
    state.aaveHistory = aaveHistory;
  },
  status(state: DefiState, status: Status) {
    state.status = status;
  },
  defiStatus(state: DefiState, status: Status) {
    state.defiStatus = status;
  },
  lendingHistoryStatus(state: DefiState, status: Status) {
    state.lendingHistoryStatus = status;
  },
  borrowingHistoryStatus(state: DefiState, status: Status) {
    state.borrowingHistoryStatus = status;
  },
  allDefiProtocols(state: DefiState, allProtocols: AllDefiProtocols) {
    state.allProtocols = allProtocols;
  },
  reset(state: DefiState) {
    Object.assign(state, defaultState());
  }
};
