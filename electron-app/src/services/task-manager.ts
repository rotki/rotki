import map from 'lodash/map';
import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import {
  BlockchainMetadata,
  ExchangeMeta,
  Task,
  TaskMeta,
  TaskType
} from '@/model/task';
import {
  ApiEventEntry,
  convertEventEntry,
  convertTradeHistoryOverview,
  TradeHistory
} from '@/model/trade-history-types';
import { convertDSRBalances, convertDSRHistory } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import {
  ApiDSRBalances,
  ApiDSRHistory,
  TaskNotFoundError
} from '@/services/types-api';
import { notify } from '@/store/notifications/utils';
import store from '@/store/store';
import { ApiAssetBalances, Severity } from '@/typing/types';
import {
  convertAssetBalances,
  convertBalances,
  convertEthBalances
} from '@/utils/conversion';

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

    store.dispatch('balances/accounts').then();
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

  private static dsrBalance(
    data: ActionResult<ApiDSRBalances>,
    _meta: TaskMeta
  ) {
    const { message, result } = data;
    if (message) {
      notify(
        `There was an issue while fetching DSR Balances: ${message}`,
        'DSR Balances',
        Severity.ERROR
      );

      return;
    }
    store.commit('balances/dsrBalances', convertDSRBalances(result));
  }

  private static dsrHistory(
    data: ActionResult<ApiDSRHistory>,
    _meta: TaskMeta
  ) {
    const { message, result } = data;
    if (message) {
      notify(
        `There was an issue while fetching DSR History: ${message}`,
        'DSR History',
        Severity.ERROR
      );

      return;
    }
    store.commit('balances/dsrHistory', convertDSRHistory(result));
  }

  monitor() {
    const state = store.state;
    const taskState = state.tasks!;
    const { tasks: taskMap, locked } = taskState;

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

      if (locked.indexOf(task.id) > -1) {
        continue;
      }

      store.commit('tasks/lock', task.id);

      api
        .queryTaskResult(task.id)
        .then(result => this.handleResult(result, task))
        .catch(e => {
          // When the request fails for any reason (pending or network error) then we unlock it
          store.commit('tasks/unlock', task.id);
          if (e instanceof TaskNotFoundError) {
            store.commit('tasks/remove', task.id);
            notify(
              `Task ${task.id}: ${task.meta.description} was not found`,
              'Task not found',
              Severity.ERROR
            );
          }
        });
    }
  }

  private handleResult(result: ActionResult<any>, task: Task<TaskMeta>) {
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
  }

  private handler: {
    [type: string]: (result: any, meta: any) => void;
  } = {
    [TaskType.QUERY_EXCHANGE_BALANCES]: TaskManager.onQueryExchangeBalances,
    [TaskType.QUERY_BLOCKCHAIN_BALANCES]: this.onQueryBlockchainBalances,
    [TaskType.TRADE_HISTORY]: this.onTradeHistory,
    [TaskType.ADD_ACCOUNT]: this.onAccountOperation,
    [TaskType.REMOVE_ACCOUNT]: this.onAccountOperation,
    [TaskType.DSR_BALANCE]: TaskManager.dsrBalance,
    [TaskType.DSR_HISTORY]: TaskManager.dsrHistory
  };

  registerHandler<R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: ActionResult<R>, meta: M) => void
  ) {
    this.handler[task] = handlerImpl;
  }

  unregisterHandler(task: TaskType) {
    delete this.handler[task];
  }
}

export const taskManager = new TaskManager();
