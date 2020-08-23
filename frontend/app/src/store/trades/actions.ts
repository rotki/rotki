import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { NewTrade, Trade, TradeUpdate } from '@/services/trades/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/store';
import { TradesState } from '@/store/trades/types';
import { ActionStatus } from '@/store/types';

export const actions: ActionTree<TradesState, RotkehlchenState> = {
  async fetchTrades({ commit }): Promise<void> {
    try {
      commit('trades', await api.trades.trades());
    } catch (e) {
      notify(`Failed: ${e}`, 'Retrieving trades', Severity.ERROR, true);
    }
  },

  async addExternalTrade({ commit }, trade: NewTrade): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      commit('addTrade', await api.trades.addExternalTrade(trade));
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async editExternalTrade({ commit }, trade: Trade): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      const updatedTrade = await api.trades.editExternalTrade(trade);
      const payload: TradeUpdate = {
        trade: updatedTrade,
        oldTradeId: trade.tradeId
      };
      commit('updateTrade', payload);
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async deleteExternalTrade(
    { commit },
    tradeId: string
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      success = await api.trades.deleteExternalTrade(tradeId);
      if (success) {
        commit('deleteTrade', tradeId);
      }
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  }
};
