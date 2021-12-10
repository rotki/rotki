import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';

export const actions: ActionTree<StatisticsState, RotkehlchenState> = {
  async fetchNetValue({ commit, rootState }) {
    try {
      const includeNfts = rootState.settings?.nftsInNetValue ?? true;
      const netValue = await api.queryNetvalueData(includeNfts);
      commit('netValue', netValue);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.statistics.net_value.error.title').toString(),
        message: i18n
          .t('actions.statistics.net_value.error.message', {
            message: e.message
          })
          .toString(),
        display: false
      });
    }
  }
};
