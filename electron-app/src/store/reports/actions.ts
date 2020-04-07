import { ActionTree } from 'vuex';
import { createTask, TaskType } from '@/model/task';
import { api } from '@/services/rotkehlchen-api';
import { notify } from '@/store/notifications/utils';
import { TaxReportState } from '@/store/reports/state';
import { Message, RotkehlchenState } from '@/store/store';
import { TaxReportEvent } from '@/typing/types';

export const actions: ActionTree<TaxReportState, RotkehlchenState> = {
  async generate({ commit }, payload: TaxReportEvent) {
    try {
      const { start, end } = payload;
      const result = await api.processTradeHistoryAsync(start, end);
      commit('reportPeriod', { start, end });
      const task = createTask(result.task_id, TaskType.TRADE_HISTORY, {
        description: 'Create tax report',
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(e.message, 'Trade History Report');
    }
  },

  async createCSV({ commit }, path: string) {
    let message: Message;
    try {
      const success = await api.exportHistoryCSV(path);
      message = {
        title: 'CSV Export',
        description: success
          ? 'History exported to CVS successfully'
          : 'History export failed',
        success
      };
    } catch (e) {
      message = {
        title: 'CSV Export',
        description: e.message,
        success: false
      };
    }
    commit('setMessage', message, { root: true });
  }
};
