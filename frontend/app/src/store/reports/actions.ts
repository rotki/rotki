import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { ReportState } from '@/store/reports/state';
import { Message, RotkehlchenState } from '@/store/types';
import { ProfitLossPeriod } from '@/typing/types';

export const actions: ActionTree<ReportState, RotkehlchenState> = {
  async generate({ commit, rootState }, payload: ProfitLossPeriod) {
    commit('accountingSettings', rootState.session!.accountingSettings);
    try {
      const { start, end } = payload;
      const result = await api.processTradeHistoryAsync(start, end);
      commit('reportPeriod', { start, end });
      const task = createTask(result.task_id, TaskType.TRADE_HISTORY, {
        title: i18n.t('actions.reports.generate.task.title').toString(),
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        e.message,
        i18n.t('actions.reports.generate.error.title').toString(),
        Severity.ERROR,
        true
      );
    }
  },

  async createCSV({ commit }, path: string) {
    let message: Message;
    try {
      const success = await api.exportHistoryCSV(path);
      message = {
        title: i18n.t('actions.reports.csv_export.title').toString(),
        description: success
          ? i18n.t('actions.reports.csv_export.message.success').toString()
          : i18n.t('actions.reports.csv_export.message.failure').toString(),
        success
      };
    } catch (e) {
      message = {
        title: i18n.t('actions.reports.csv_export.title').toString(),
        description: e.message,
        success: false
      };
    }
    commit('setMessage', message, { root: true });
  }
};
