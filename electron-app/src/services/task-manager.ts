import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import store from '@/store/store';
import {
  convertAssetBalances,
  convertBalances,
  convertEthBalances
} from '@/utils/conversion';
import {
  BlockchainMetadata,
  ExchangeMeta,
  TaskMeta,
  TaskType
} from '@/model/task';
import { notify } from '@/store/notifications/utils';
import { api } from '@/services/rotkehlchen-api';
import {
  ApiEventEntry,
  convertEventEntry,
  convertTradeHistoryOverview,
  TradeHistory
} from '@/model/trade-history-types';
import map from 'lodash/map';
import { ApiAssetBalances, Severity } from '@/typing/types';

export class TaskManager {
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

  onAccountOperation(
    data: ActionResult<BlockchainBalances>,
    meta: BlockchainMetadata
  ) {
    const { result, message } = data;
    const { description, blockchain } = meta;

    if (message) {
      notify(`Operation failed due to ${message}`, description);
      return;
    }
    const { per_account, totals } = result;
    const { ETH, BTC } = per_account;

    if (blockchain === 'ETH') {
      store.commit('balances/updateEth', convertEthBalances(ETH));
    } else {
      store.commit('balances/updateBtc', convertBalances(BTC));
    }
    store.commit('balances/updateTotals', convertBalances(totals));
  }

  onTradeHistory(data: ActionResult<TradeHistory>, _meta: TaskMeta) {
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
    const state = store.state;
    const taskState = state.tasks!;
    const { tasks: taskMap, processingTasks } = taskState;

    for (const id in taskMap) {
      if (!Object.prototype.hasOwnProperty.call(taskMap, id)) {
        continue;
      }
      const task = taskMap[id];
      if (task.id == null) {
        notify(
          `Task ${task.type} -> ${task.meta.description} had a null identifier`,
          'Invalid task found',
          Severity.WARNING
        );
        continue;
      }

      if (processingTasks.indexOf(task.id) > -1) {
        return;
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

          store.commit('tasks/processing', task.id);
          try {
            handler(result, task.meta);
          } catch (e) {
            notify(
              `An error occurred while processing task [${task.id}] '${task.meta.description}': ${e}`,
              'Task processing failed',
              Severity.ERROR
            );
          }
          store.commit('tasks/remove', task.id);
        })
        .catch(() => {});
    }
  }

  readonly handler: {
    [type: string]: (result: any, meta: any) => void;
  } = {
    [TaskType.QUERY_EXCHANGE_BALANCES]: TaskManager.onQueryExchangeBalances,
    [TaskType.QUERY_BLOCKCHAIN_BALANCES]: this.onQueryBlockchainBalances,
    [TaskType.TRADE_HISTORY]: this.onTradeHistory,
    [TaskType.ADD_ACCOUNT]: this.onAccountOperation,
    [TaskType.REMOVE_ACCOUNT]: this.onAccountOperation
  };
}

export const taskManager = new TaskManager();
