import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaxReportState } from '@/store/reports/state';
import { Severity, TaxReportEvent } from '@/typing/types';
import { service } from '@/services/rotkehlchen_service';
import { notify } from '@/store/notifications/utils';
import { createTask, TaskType } from '@/model/task';

export const actions: ActionTree<TaxReportState, RotkehlchenState> = {
  async generate({ commit }, payload: TaxReportEvent) {
    try {
      const { start, end } = payload;
      const result = await service.process_trade_history_async(start, end);
      commit('reportPeriod', { start, end });
      const task = createTask(
        result.task_id,
        TaskType.TRADE_HISTORY,
        'Create tax report',
        true
      );
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(e.message, 'Trade History Report');
    }
  },

  async createCSV(_, path: string) {
    service
      .export_processed_history_csv(path)
      .then(() => {
        console.log('dd');
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
