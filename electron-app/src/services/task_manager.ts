//todo move to new class TASK Manager
import { monitor_add_callback } from '@/legacy/monitor';
import { ActionResult } from '@/model/action-result';
import { BlockchainBalances } from '@/model/blockchain-balances';
import store from '@/store';
import { convertEthBalances } from '@/utils/conversion';

monitor_add_callback(
  'user_settings_query_blockchain_balances',
  (result: ActionResult<BlockchainBalances>) => {
    let msg = 'Querying blockchain balances for user settings failed';
    if (result == null || result.message !== '') {
      if (result.message !== '') {
        msg = result.message;
      }
      //showError('Querying Blockchain Balances Error', msg);
      return;
    }

    store.commit(
      'addPerAccountEth',
      convertEthBalances(result.result.per_account['ETH'])
    );
    console.log(result.result);
  }
);
