import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaxReportState } from '@/store/reports/state';
import { Severity, TaxReportEvent } from '@/typing/types';
import { api } from '@/services/rotkehlchen-api';
import { notify } from '@/store/notifications/utils';
import { createTask, TaskType } from '@/model/task';

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

  async createCSV(_, path: string) {
    api
      .exportHistoryCSV(path)
      .then(() => {
        notify(
          'History exported to CVS successfully',
          'CSV Export',
          Severity.INFO
        );
      })
      .catch((reason: Error) => {
        notify(reason.message, 'CSV Export', Severity.ERROR);
      });
  }
};
