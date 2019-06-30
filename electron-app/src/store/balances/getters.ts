import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store';
import { BalanceState } from '@/store/balances/state';
import {
  AccountBalance,
  AssetBalance,
  Balance,
  EthBalance
} from '@/model/blockchain-balances';
import map from 'lodash/map';

export const getters: GetterTree<BalanceState, RotkehlchenState> = {
  ethAccounts(state: BalanceState): AccountBalance[] {
    return map(state.eth, (value: EthBalance, account: string) => {
      const accountBalance: AccountBalance = {
        account,
        amount: value.eth,
        usdValue: value.usdValue
      };
      return accountBalance;
    });
  },
  btcAccounts(state: BalanceState): AccountBalance[] {
    return map(state.btc, (value: Balance, account: string) => {
      const accountBalance: AccountBalance = {
        account,
        ...value
      };
      return accountBalance;
    });
  },
  totals(state: BalanceState): AssetBalance[] {
    return map(state.totals, (value: Balance, asset: string) => {
      const assetBalance: AssetBalance = {
        asset,
        ...value
      };
      return assetBalance;
    });
  }
};
