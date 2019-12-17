import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import store from '@/store/store';
import {
  convertAssetBalances,
  convertBalances,
  convertEthBalances
} from '@/utils/conversion';
import { ExchangeBalanceResult } from '@/model/exchange-balance-result';
import { TaskType } from '@/model/task';
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
import { Severity } from '@/typing/types';

export class TaskManager {
  private static onUserSettingsQueryBlockchainBalances(
    result: ActionResult<BlockchainBalances>
  ) {
    let msg: string = '';
    if (!result) {
      msg = 'Querying blockchain balances for user settings failed';
    } else if (result.message !== '') {
      msg = result.message;
    }

    if (msg) {
      notify(msg);
      return;
    }

    const { result: data } = result;
    const { per_account, totals } = data;
    const { ETH, BTC } = per_account;

    store.commit('balances/updateEth', convertEthBalances(ETH));
    store.commit('balances/updateBtc', convertBalances(BTC));
    store.commit('balances/updateTotals', convertBalances(totals));
  }

  private static onQueryExchangeBalances(result: ExchangeBalanceResult) {
    if (result.error) {
      notify(
        `Querying ${result.name} failed because of: ${result.error}. Check the logs for more details.`,
        'Exchange Query Error'
      );
      return;
    }

    const { name, balances } = result;

    store.commit('balances/addExchangeBalances', {
      name,
      balances: convertAssetBalances(balances)
    });

    if (!balances) {
      notify(
        `Querying ${result.name} failed. Result contains no balances. Check the logs for more details.`,
        'Exchange Query Error'
      );
      return;
    }
  }

  onQueryBlockchainBalances(result: ActionResult<BlockchainBalances>) {
    if (result.message !== '') {
      notify(
        `Querying blockchain balances died because of: ${result.message}. Check the logs for more details.`,
        'Blockchain Query Error'
      );
      return;
    }

    const { result: data } = result;
    const { per_account, totals } = data;
    const { ETH, BTC } = per_account;

    store.commit('balances/updateEth', convertEthBalances(ETH));
    store.commit('balances/updateBtc', convertBalances(BTC));
    store.commit('balances/updateTotals', convertBalances(totals));
  }

  onTradeHistory(tradeHistoryResult: ActionResult<TradeHistoryResult>) {
    const { message, result } = tradeHistoryResult;

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
    const tasks: TaskMap = store.state.tasks!.tasks;
    for (const id in tasks) {
      if (!Object.prototype.hasOwnProperty.call(tasks, id)) {
        continue;
      }
      const task = tasks[id];
      if (task.id == null) {
        notify(
          JSON.stringify(task, null, 4),
          'Task with null id',
          Severity.INFO
        );
        continue;
      }

      api.queryTaskResult(task.id).then(result => {
        if (!task.asyncResult) {
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

        handler(result);
        store.commit('tasks/remove', task.id);
      });
    }
  }

  readonly handler: { [type: string]: (result: any) => void } = {
    [TaskType.USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES]:
      TaskManager.onUserSettingsQueryBlockchainBalances,
    [TaskType.QUERY_EXCHANGE_BALANCES]: TaskManager.onQueryExchangeBalances,
    [TaskType.QUERY_BLOCKCHAIN_BALANCES]: this.onQueryBlockchainBalances,
    [TaskType.TRADE_HISTORY]: this.onTradeHistory
  };
}

export const taskManager = new TaskManager();
