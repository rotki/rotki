import { MutationTree } from 'vuex';
import { Trade, TradeUpdate } from '@/services/trades/types';
import { Status } from '@/store/const';
import { defaultState } from '@/store/trades/state';
import { TradesState } from '@/store/trades/types';

export const mutations: MutationTree<TradesState> = {
  appendTrades(state: TradesState, trades: Trade[]) {
    state.trades = [...state.trades, ...trades];
  },

  updateLimit(state: TradesState, limit: number) {
    state.limit = limit;
  },

  trades(state: TradesState, trades: Trade[]) {
    state.trades = trades;
  },

  status(state: TradesState, status: Status) {
    state.status = status;
  },

  addTrade(state: TradesState, trade: Trade) {
    state.trades.push(trade);
  },

  updateTrade(state: TradesState, { trade, oldTradeId }: TradeUpdate) {
    const index = state.trades.findIndex(exTrade => {
      return exTrade.tradeId === oldTradeId;
    });
    Object.assign(state.trades[index], trade);
  },

  deleteTrade(state: TradesState, tradeId: string) {
    const index = state.trades.findIndex(trade => trade.tradeId === tradeId);
    state.trades.splice(index, 1);
  },

  reset(state: TradesState) {
    Object.assign(state, defaultState());
  }
};
