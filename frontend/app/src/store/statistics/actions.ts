import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';

export const actions: ActionTree<StatisticsState, RotkehlchenState> = {
  async fetchNetValue({ commit }) {
    try {
      const netValue = await api.queryNetvalueData();
      commit('netValue', netValue);
    } catch (e) {
      notify(`Failed: ${e}`, 'Retrieving net value data', Severity.ERROR);
    }
  }
};
