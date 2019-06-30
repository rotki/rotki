//todo move to new class TASK Manager
import { monitor_add_callback } from '@/legacy/monitor';
import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import store from '@/store';
import { convertBalances, convertEthBalances } from '@/utils/conversion';
import { ExchangeBalanceResult } from '@/model/exchange-balance-result';
import { TaskType } from '@/model/task';
import { notify } from '@/notifications/utils';

monitor_add_callback(
  TaskType.USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES,
  (result: ActionResult<BlockchainBalances>) => {
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
);

// add callbacks for dashboard to the monitor
monitor_add_callback(
  TaskType.QUERY_EXCHANGE_BALANCES,
  (result: ExchangeBalanceResult) => {
    if (result.error) {
      notify(
        `Querying ${result.name} failed because of: ${result.error}. Check the logs for more details.`,
        'Exchange Query Error'
      );
      return;
    }
    const balances = result.balances;
    store.commit('addExchangeBalances', {
      name: result.name,
      balances: result.balances || {}
    });
    if (!balances) {
      notify(
        `Querying ${result.name} failed. Result contains no balances. Check the logs for more details.`,
        'Exchange Query Error'
      );
      return;
    }
    console.log(result);
  }
);

monitor_add_callback(
  TaskType.QUERY_BLOCKCHAIN_BALANCES,
  (result: ActionResult<BlockchainBalances>) => {
    if (result.message !== '') {
      notify(
        `Querying blockchain balances died because of: ${result.message}. Check the logs for more details.`,
        'Blockchain Query Error'
      );
      return;
    }

    console.log(result);
    const { result: data } = result;
    const { per_account, totals } = data;
    const { ETH, BTC } = per_account;

    store.commit('balances/updateEth', convertEthBalances(ETH));
    store.commit('balances/updateBtc', convertBalances(BTC));
    store.commit('balances/updateTotals', convertBalances(totals));
  }
);
