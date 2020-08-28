import { MutationTree } from 'vuex';
import { AssetMovement, Trade, TradeUpdate } from '@/services/history/types';
import { LimitedResponse } from '@/services/types-api';
import { defaultHistoricState, defaultState } from '@/store/history/state';
import { HistoryState } from '@/store/history/types';

export const mutations: MutationTree<HistoryState> = {
  appendTrades(state: HistoryState, trades: LimitedResponse<Trade[]>) {
    state.trades = {
      data: [...state.trades.data, ...trades.entries],
      limit: trades.entriesLimit,
      found: trades.entriesFound
    };
  },

  resetTrades(state: HistoryState) {
    state.trades = defaultHistoricState();
  },

  addTrade(state: HistoryState, trade: Trade) {
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

  updateMovements(
    state: HistoryState,
    movements: LimitedResponse<AssetMovement[]>
  ) {
    state.assetMovements = {
      data: [...state.assetMovements.data, ...movements.entries],
      limit: movements.entriesLimit,
      found: movements.entriesFound
    };
  },
  resetMovements(state: HistoryState) {
    state.assetMovements = defaultHistoricState();
  },

  reset(state: HistoryState) {
    Object.assign(state, defaultState());
  }
};
