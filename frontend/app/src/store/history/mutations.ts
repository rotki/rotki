import { MutationTree } from 'vuex';
import { TradeUpdate } from '@/services/history/types';
import { HistoryMutations } from '@/store/history/consts';
import { defaultState } from '@/store/history/state';
import {
  AssetMovements,
  EthTransactions,
  HistoricData,
  HistoryState,
  LedgerActionEntry,
  TradeEntry,
  Trades
} from '@/store/history/types';

export const mutations: MutationTree<HistoryState> = {
  [HistoryMutations.SET_TRADES](state: HistoryState, trades: Trades) {
    state.trades = trades;
  },

  [HistoryMutations.ADD_TRADE](state: HistoryState, trade: TradeEntry) {
    const { data: trades } = state.trades;
    state.trades = { ...state.trades, data: [...trades, trade] };
  },

  [HistoryMutations.UPDATE_TRADE](
    state: HistoryState,
    { trade, oldTradeId }: TradeUpdate
  ) {
    const { data: trades } = state.trades;
    const update = [...trades];
    const index = update.findIndex(exTrade => {
      return exTrade.tradeId === oldTradeId;
    });
    update[index] = trade;
    state.trades = {
      ...state.trades,
      data: update
    };
  },

  [HistoryMutations.DELETE_TRADE](state: HistoryState, tradeId: string) {
    const { data: trades } = state.trades;
    const data = [...trades.filter(trade => trade.tradeId !== tradeId)];
    state.trades = {
      ...state.trades,
      data
    };
  },

  [HistoryMutations.SET_MOVEMENTS](
    state: HistoryState,
    movements: AssetMovements
  ) {
    state.assetMovements = movements;
  },

  [HistoryMutations.SET_TRANSACTIONS](
    state: HistoryState,
    transactions: EthTransactions
  ) {
    state.transactions = transactions;
  },

  [HistoryMutations.SET_LEDGER_ACTIONS](
    state: HistoryState,
    actions: HistoricData<LedgerActionEntry>
  ) {
    state.ledgerActions = actions;
  },

  [HistoryMutations.ADD_LEDGER_ACTION](
    state: HistoryState,
    action: LedgerActionEntry
  ) {
    const ledgerActions = state.ledgerActions;
    state.ledgerActions = {
      data: [...ledgerActions.data, action],
      limit: ledgerActions.limit,
      found: ledgerActions.found + 1
    };
  },

  [HistoryMutations.RESET](state: HistoryState) {
    Object.assign(state, defaultState());
  }
};
