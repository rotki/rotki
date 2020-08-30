import { ActionTree } from 'vuex';
import { createTask } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { TaxReportState } from '@/store/reports/state';
import { Message, RotkehlchenState } from '@/store/types';
import { TaxReportEvent } from '@/typing/types';

export const actions: ActionTree<TaxReportState, RotkehlchenState> = {
  async generate({ commit }, payload: TaxReportEvent) {
    try {
      const { start, end } = payload;
      const result = await api.processTradeHistoryAsync(start, end);
      commit('reportPeriod', { start, end });
      const task = createTask(result.task_id, TaskType.TRADE_HISTORY, {
        title: 'Create tax report',
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(e.message, 'Trade History Report', Severity.ERROR, true);
    }
  },

  async createCSV({ commit }, path: string) {
    let message: Message;
    try {
      const success = await api.exportHistoryCSV(path);
      message = {
        title: 'CSV Export',
        description: success
          ? 'History exported to CSV successfully'
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
