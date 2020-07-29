import { MutationTree } from 'vuex';
import { defaultState } from '@/store/trades/state';
import { Status } from '@/store/trades/status';
import { Trade, TradesState } from '@/store/trades/types';

export const mutations: MutationTree<TradesState> = {
  allTrades(state: TradesState, trades: Trade[]) {
    state.allTrades = trades;
  },
  externalTrades(state: TradesState, trades: Trade[]) {
    state.externalTrades = trades;
  },
  status(state: TradesState, status: Status) {
    state.status = status;
  },

  addTrade(state: TradesState, trade: Trade) {
    // TODO: when we're not using "externalTrades" as the "master" trades store, change this to allTrades
    state.externalTrades.push(trade);
  },

  updateTrade(state: TradesState, { originalTrade, updatedTrade }) {
    const updatedTradeIndex = state.externalTrades.findIndex(trade => {
      return trade.tradeId === originalTrade.tradeId;
    });
    Object.assign(state.externalTrades[updatedTradeIndex], updatedTrade);
  },

  deleteTrade(state: TradesState, tradeId: string) {
    // TODO: when we're not using "externalTrades" as the "master" trades store, change this to allTrades
    const deletedTradeIndex = state.externalTrades.findIndex(
      trade => trade.tradeId === tradeId
    );
    state.externalTrades.splice(deletedTradeIndex, 1);
  },

  reset(state: TradesState) {
    Object.assign(state, defaultState());
  }
};
