import { MutationTree } from 'vuex';
import { AaveBalances, AaveHistory } from '@/services/defi/types/aave';
import {
  CompoundBalances,
  CompoundHistory
} from '@/services/defi/types/compound';
import { UniswapBalances } from '@/services/defi/types/uniswap';
import {
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { DefiMutations } from '@/store/defi/mutation-types';
import { defaultState } from '@/store/defi/state';
import {
  Airdrops,
  AllDefiProtocols,
  BalancerBalances,
  DefiState,
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  MakerDAOVaultDetails,
  UniswapEvents,
  DexTrades,
  BalancerEvents
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
  allDefiProtocols(state: DefiState, allProtocols: AllDefiProtocols) {
    state.allProtocols = allProtocols;
  },
  compoundBalances(state: DefiState, balances: CompoundBalances) {
    state.compoundBalances = balances;
  },
  compoundHistory(state: DefiState, history: CompoundHistory) {
    state.compoundHistory = history;
  },
  [DefiMutations.YEARN_VAULTS_BALANCES](
    state: DefiState,
    balances: YearnVaultsBalances
  ) {
    state.yearnVaultsBalances = balances;
  },
  [DefiMutations.YEARN_VAULTS_HISTORY](
    state: DefiState,
    history: YearnVaultsHistory
  ) {
    state.yearnVaultsHistory = history;
  },
  [DefiMutations.YEARN_VAULTS_V2_BALANCES](
    state: DefiState,
    balances: YearnVaultsBalances
  ) {
    state.yearnVaultsV2Balances = balances;
  },
  [DefiMutations.YEARN_VAULTS_V2_HISTORY](
    state: DefiState,
    history: YearnVaultsHistory
  ) {
    state.yearnVaultsV2History = history;
  },
  uniswapBalances(state: DefiState, balances: UniswapBalances) {
    state.uniswapBalances = balances;
  },
  uniswapTrades(state: DefiState, trades: DexTrades) {
    state.uniswapTrades = trades;
  },
  uniswapEvents(state: DefiState, events: UniswapEvents) {
    state.uniswapEvents = events;
  },
  airdrops(state: DefiState, airdrops: Airdrops) {
    state.airdrops = airdrops;
  },
  balancerBalances(state: DefiState, balances: BalancerBalances) {
    state.balancerBalances = balances;
  },
  balancerTrades(state: DefiState, trades: DexTrades) {
    state.balancerTrades = trades;
  },
  balancerEvents(state: DefiState, events: BalancerEvents) {
    state.balancerEvents = events;
  },
  reset(state: DefiState) {
    Object.assign(state, defaultState());
  }
};
