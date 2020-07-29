import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { ApiTrade } from '@/services/types-api';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/store';
import { convertTrade, convertTrades } from '@/store/trades/converters';
import { TradesState } from '@/store/trades/types';

export const actions: ActionTree<TradesState, RotkehlchenState> = {
  async fetchTrades({ commit }): Promise<void> {
    try {
      const trades: ApiTrade[] = await api.allTrades();
      commit('allTrades', convertTrades(trades));
    } catch (e) {
      notify(`Failed: ${e}`, 'Retrieving trades', Severity.ERROR);
    }
  },

  async fetchExternalTrades({ commit }): Promise<void> {
    try {
      const trades: ApiTrade[] = await api.externalTrades();
      commit('externalTrades', convertTrades(trades));
    } catch (e) {
      notify(`Failed: ${e}`, 'Retrieving external trades', Severity.ERROR);
    }
  },

  async addExternalTrade(
    { commit },
    trade: Omit<ApiTrade, 'trade_id'>
  ): Promise<{ result: boolean; error: string }> {
    let result = false;
    let error = '';
    try {
      const newTrade = await api.addExternalTrade(trade);
      commit('addTrade', convertTrade(newTrade));
      result = true;
    } catch (e) {
      result = false;
      error = e;
    }
    return { result, error };
  },

  async editExternalTrade(
    { commit },
    trade: ApiTrade
  ): Promise<{ result: boolean; error: string }> {
    let result = false;
    let error = '';
    try {
      // const updatedTrade: Trade;
      const originalTrade = convertTrade(trade);
      const editedTrade = await api.editExternalTrade(trade);
      const updatedTrade = convertTrade(editedTrade);
      const mutationParams = { originalTrade, updatedTrade };
      // updatedTrade = convertTrade(updatedTrade);
      commit('updateTrade', mutationParams);
      result = true;
    } catch (e) {
      result = false;
      error = e;
    }
    return { result, error };
  },

  async deleteExternalTrade({ commit }, tradeId: string) {
    let result = false;
    try {
      const success = await api.deleteExternalTrade(tradeId);
      if (success) {
        commit('deleteTrade', tradeId);
        result = true;
      }
    } catch (e) {
      result = false;
    }
    return result;
  }

  // async editExternalTrade({ commit }, balance: ApiTrade) {
  //   let result = false;
  //   try {
  //     const manualBalances = await api.editExternalTrade([balance]);
  //     commit('manualBalances', convertManualBalances(manualBalances));
  //     result = true;
  //   } catch (e) {
  //     commit(
  //       'setMessage',
  //       {
  //         title: 'Adding Manual Balance',
  //         description: `${e.message}`
  //       } as Message,
  //       { root: true }
  //     );
  //   }
  //   return result;
  // },
};
