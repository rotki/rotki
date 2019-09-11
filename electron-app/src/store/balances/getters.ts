import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
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

  exchanges: (state: BalanceState) => {
    const balances = state.exchangeBalances;
    return Object.keys(balances).map(value => ({
      name: value,
      balances: balances[value],
      totals: assetSum(balances[value])
    }));
  },

  aggregatedBalances: (state: BalanceState, getters) => {
    const currencyBalances = state.fiatBalances.map(
      value =>
        ({
          asset: value.currency,
          amount: value.amount,
          usdValue: value.usdValue
        } as AssetBalance)
    );

    return currencyBalances.concat(getters.totals);
  },

  fiatTotal: (state: BalanceState) => {
    return state.fiatBalances.reduce((sum, balance) => {
      return sum.plus(balance.usdValue);
    }, Zero);
  },

  blockchainTotal: (state: BalanceState, getters) => {
    return getters.totals.reduce((sum: BigNumber, asset: AssetBalance) => {
      return sum.plus(asset.usdValue);
    }, Zero);
  }
};
