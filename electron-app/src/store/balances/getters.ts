import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store';
import { BalanceState } from '@/store/balances/state';
import {
  AccountBalance,
  AssetBalance,
  Balance,
  EthBalance,
  FiatBalance
} from '@/model/blockchain-balances';
import map from 'lodash/map';
import BigNumber from 'bignumber.js';
import reduce from 'lodash/reduce';
import { Zero } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';

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
  },
  exchangeRate: (state: BalanceState) => (currency: string) => {
    return state.usdToFiatExchangeRates[currency];
  },

  fiatTotals: (state: BalanceState): BigNumber => {
    return reduce(
      state.fiatBalances,
      (result: BigNumber, value: FiatBalance) => {
        return result.plus(value.usdValue);
      },
      Zero
    );
  },
  exchanges: (state: BalanceState) => {
    const balances = state.exchangeBalances;
    return Object.keys(balances).map(value => ({
      name: value,
      balances: balances[value],
      totals: assetSum(balances[value])
    }));
  }
};
