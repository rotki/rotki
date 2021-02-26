import { MutationTree } from 'vuex';
import { TradeUpdate } from '@/services/history/types';
import {
  MUTATION_ADD_LEDGER_ACTION,
  MUTATION_SET_LEDGER_ACTIONS
} from '@/store/history/consts';
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
  setTrades(state: HistoryState, trades: Trades) {
    state.trades = trades;
  },

  addTrade(state: HistoryState, trade: TradeEntry) {
    const { data: trades } = state.trades;
    state.trades = { ...state.trades, data: [...trades, trade] };
  },

  updateTrade(state: HistoryState, { trade, oldTradeId }: TradeUpdate) {
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

  deleteTrade(state: HistoryState, tradeId: string) {
    const { data: trades } = state.trades;
    const data = [...trades.filter(trade => trade.tradeId !== tradeId)];
    state.trades = {
      ...state.trades,
      data
    };
  },

  setMovements(state: HistoryState, movements: AssetMovements) {
    state.assetMovements = movements;
  },

  setTransactions(state: HistoryState, transactions: EthTransactions) {
    state.transactions = transactions;
  },

  [MUTATION_SET_LEDGER_ACTIONS](
    state: HistoryState,
    actions: HistoricData<LedgerActionEntry>
  ) {
    state.ledgerActions = actions;
  },

  [MUTATION_ADD_LEDGER_ACTION](state: HistoryState, action: LedgerActionEntry) {
    const ledgerActions = state.ledgerActions;
    state.ledgerActions = {
      data: [...ledgerActions.data, action],
      limit: ledgerActions.limit,
      found: ledgerActions.found + 1
    };
  },

  reset(state: HistoryState) {
    Object.assign(state, defaultState());
  }
};
