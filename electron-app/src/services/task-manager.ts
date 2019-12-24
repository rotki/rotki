import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import store from '@/store/store';
import {
  convertAssetBalances,
  convertBalances,
  convertEthBalances
} from '@/utils/conversion';
import { ExchangeMeta, TaskMeta, TaskType } from '@/model/task';
import { notify } from '@/store/notifications/utils';
import { api } from '@/services/rotkehlchen-api';
import { TaskMap } from '@/store/tasks/state';
import {
  ApiEventEntry,
  convertEventEntry,
  convertTradeHistoryOverview,
  TradeHistoryResult
} from '@/model/trade-history-types';
import map from 'lodash/map';
import { ApiAssetBalances, Severity } from '@/typing/types';

export class TaskManager {
  private static onUserSettingsQueryBlockchainBalances(
    payload: ActionResult<BlockchainBalances>,
    _meta: TaskMeta
  ) {
    const { result, message } = payload;

    if (message) {
      notify(message, 'Blockchain query error');
      return;
    }

    const { per_account, totals } = result;
    const { ETH, BTC } = per_account;

    store.commit('balances/updateEth', convertEthBalances(ETH));
    store.commit('balances/updateBtc', convertBalances(BTC));
    store.commit('balances/updateTotals', convertBalances(totals));
  }

  private static onQueryExchangeBalances(
    payload: ActionResult<ApiAssetBalances>,
    meta: ExchangeMeta
  ) {
    const { result, message } = payload;

    if (message) {
      notify(message, 'Exchange Query Error ');
      return;
    }

    store.commit('balances/addExchangeBalances', {
      name: meta.name,
      balances: convertAssetBalances(result)
    });
  }

  onQueryBlockchainBalances(
    data: ActionResult<BlockchainBalances>,
    _meta: TaskMeta
  ) {
    const { result, message } = data;

    if (message) {
      notify(
        `Querying blockchain balances died because of: ${message}. Check the logs for more details.`,
        'Blockchain Query Error'
      );
      return;
    }

    const { per_account, totals } = result;
    const { ETH, BTC } = per_account;

    store.commit('balances/updateEth', convertEthBalances(ETH));
    store.commit('balances/updateBtc', convertBalances(BTC));
    store.commit('balances/updateTotals', convertBalances(totals));
  }

  onTradeHistory(data: ActionResult<TradeHistoryResult>, _meta: TaskMeta) {
    const { message, result } = data;

    if (message) {
      notify(
        `During trade history query we got:${message}. History report is probably not complete.`,
        'Trade History Query Warning'
      );
    }

    const { overview, all_events } = result;

    const payload = {
      overview: convertTradeHistoryOverview(overview),
      events: map(all_events, (event: ApiEventEntry) =>
        convertEventEntry(event)
      )
    };
    store.commit('reports/set', payload);
  }

  monitor() {
    const tasks: TaskMap<TaskMeta> = store.state.tasks!.tasks;
    for (const id in tasks) {
      if (!Object.prototype.hasOwnProperty.call(tasks, id)) {
        continue;
      }
      const task = tasks[id];
      if (task.id == null) {
        notify(
          `Task ${task.type} -> ${task.meta.description} had a null identifier`,
          'Invalid task found',
          Severity.WARNING
        );
        continue;
      }
      api
        .queryTaskResult(task.id)
        .then(result => {
          if (task.meta.ignoreResult) {
            store.commit('tasks/remove', task.id);
            return;
          }

          if (result == null) {
            return;
          }

          const handler = this.handler[task.type];

          if (!handler) {
            notify(
              `No handler found for task '${task.type}' with id ${task.id}`,
              'Tasks',
              Severity.INFO
            );
            return;
          }

          handler(result, task.meta);
          store.commit('tasks/remove', task.id);
        })
        .catch(() => {});
    }
  }

  readonly handler: {
    [type: string]: (result: any, meta: any) => void;
  } = {
    [TaskType.USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES]:
      TaskManager.onUserSettingsQueryBlockchainBalances,
    [TaskType.QUERY_EXCHANGE_BALANCES]: TaskManager.onQueryExchangeBalances,
    [TaskType.QUERY_BLOCKCHAIN_BALANCES]: this.onQueryBlockchainBalances,
    [TaskType.TRADE_HISTORY]: this.onTradeHistory
  };
}

export const taskManager = new TaskManager();
