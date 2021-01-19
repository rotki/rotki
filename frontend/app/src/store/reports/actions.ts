import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { TradeHistory } from '@/model/trade-history-types';
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
      const { taskId } = await api.processTradeHistoryAsync(start, end);
      commit('reportPeriod', { start, end });
      const task = createTask(taskId, TaskType.TRADE_HISTORY, {
        title: i18n.t('actions.reports.generate.task.title').toString(),
        numericKeys: [
          'paid_in_asset',
          'taxable_amount',
          'paid_in_profit_currency',
          'taxable_bought_cost_in_profit_currency',
          'taxable_received_in_profit_currency',
          'received_in_asset',
          'net_profit_or_loss',
          'loan_profit',
          'defi_profit_loss',
          'margin_positions_profit_loss',
          'ledger_actions_profit_loss',
          'settlement_losses',
          'ethereum_transaction_gas_costs',
          'asset_movement_fees',
          'general_trade_profit_loss',
          'taxable_trade_profit_loss',
          'total_taxable_profit_loss',
          'total_profit_loss'
        ],
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<TradeHistory, TaskMeta>(
        TaskType.TRADE_HISTORY
      );
      const { overview, allEvents } = result;

      const report = {
        overview: overview,
        events: allEvents
      };
      commit('set', report);
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
