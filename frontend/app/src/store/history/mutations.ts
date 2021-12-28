import { MutationTree } from 'vuex';
import { IgnoredActions } from '@/services/history/const';
import { TradeLocation } from '@/services/history/types';
import { HistoryMutations } from '@/store/history/consts';
import { defaultState } from '@/store/history/state';
import {
  AssetMovementEntry,
  EthTransactionEntry,
  HistoryState,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import { Collection } from '@/types/collection';

export const mutations: MutationTree<HistoryState> = {
  [HistoryMutations.SET_ASSOCIATED_LOCATIONS](
    state: HistoryState,
    associatedLocations: TradeLocation[]
  ) {
    state.associatedLocations = associatedLocations;
  },

  [HistoryMutations.SET_TRADES](
    state: HistoryState,
    trades: Collection<TradeEntry>
  ) {
    state.trades = trades;
  },

  [HistoryMutations.SET_MOVEMENTS](
    state: HistoryState,
    movements: Collection<AssetMovementEntry>
  ) {
    state.assetMovements = movements;
  },

  [HistoryMutations.SET_TRANSACTIONS](
    state: HistoryState,
    transactions: Collection<EthTransactionEntry>
  ) {
    state.transactions = transactions;
  },

  [HistoryMutations.SET_LEDGER_ACTIONS](
    state: HistoryState,
    actions: Collection<LedgerActionEntry>
  ) {
    state.ledgerActions = actions;
  },

  [HistoryMutations.SET_IGNORED](state: HistoryState, ignored: IgnoredActions) {
    state.ignored = ignored;
  },

  [HistoryMutations.RESET](state: HistoryState) {
    Object.assign(state, defaultState());
  }
};
