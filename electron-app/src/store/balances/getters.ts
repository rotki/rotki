import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { BalanceState } from '@/store/balances/state';
import {
  AccountBalance,
  AssetBalance,
  Balance,
  EthBalance
} from '@/model/blockchain-balances';
import map from 'lodash/map';
import BigNumber from 'bignumber.js';
import { Zero } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';
import isEmpty from 'lodash/isEmpty';

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
      total: assetSum(balances[value])
    }));
  },

  exchangeBalances: (state: BalanceState) => (
    exchange: string
  ): AssetBalance[] => {
    const exchangeBalances = state.exchangeBalances[exchange];
    return exchangeBalances
      ? Object.keys(exchangeBalances).map(
          asset =>
            ({
              asset,
              amount: exchangeBalances[asset].amount,
              usdValue: exchangeBalances[asset].usdValue
            } as AssetBalance)
        )
      : [];
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

    const exchangeBalances = state.connectedExchanges
      .map(exchange => getters.exchangeBalances(exchange))
      .reduce(
        (previousValue, currentValue) => previousValue.concat(currentValue),
        new Array<AssetBalance>()
      );

    const balances = currencyBalances
      .concat(getters.totals)
      .concat(exchangeBalances)
      .reduce(
        (accumulator, assetBalance) => {
          const balance = accumulator[assetBalance.asset];
          if (!balance) {
            accumulator[assetBalance.asset] = assetBalance;
          } else {
            balance.amount.plus(assetBalance.amount);
            balance.usdValue.plus(assetBalance.usdValue);
          }
          return accumulator;
        },
        {} as { [asset: string]: AssetBalance }
      );
    return Object.values(balances);
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
  },

  accountTokens: (state: BalanceState) => (account: string) => {
    const ethAccount = state.eth[account];
    if (!ethAccount || isEmpty(ethAccount)) {
      return [];
    }

    return Object.entries(ethAccount.tokens).map(
      ([key, value]) =>
        ({
          asset: key,
          amount: value,
          usdValue: Zero
        } as AssetBalance)
    );
  }
};
