import { default as BigNumber } from 'bignumber.js';
import { aggregateTotal } from '@/filters';
import { NetValue } from '@/services/types-api';
import { AssetBalance } from '@/store/balances/types';
import { StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { bigNumberify, Zero } from '@/utils/bignumbers';

interface StatisticsGetters {
  netValue: (startingDate: number) => NetValue;
  totalNetWorth: BigNumber;
  totalNetWorthUsd: BigNumber;
}

export const getters: Getters<
  StatisticsState,
  StatisticsGetters,
  RotkehlchenState,
  any
> = {
  netValue: (
    state,
    getters,
    _rootState,
    {
      'balances/exchangeRate': exchangeRate,
      'session/currencySymbol': currency
    }
  ) => (startingDate: number): NetValue => {
    function convert(value: string | number | BigNumber): number {
      const bigNumber =
        typeof value === 'string' || typeof value === 'number'
          ? bigNumberify(value)
          : value;
      const convertedValue =
        currency === 'USD'
          ? bigNumber
          : bigNumber.multipliedBy(exchangeRate(currency));
      return convertedValue.toNumber();
    }

    const { times, data } = state.netValue;
    const netValue: NetValue = { times: [], data: [] };
    if (times.length === 0 && data.length === 0) {
      return netValue;
    }

    for (let i = 0; i < times.length; i++) {
      const time = times[i];
      if (time < startingDate) {
        continue;
      }
      netValue.times.push(time);
      netValue.data.push(convert(data[i]));
    }

    return {
      times: [...netValue.times, new Date().getTime() / 1000],
      data: [...netValue.data, getters.totalNetWorth.toNumber()]
    };
  },

  totalNetWorth: (
    state,
    getters,
    _rootState,
    {
      'balances/aggregatedBalances': aggregatedBalances,
      'balances/liabilities': liabilities,
      'balances/exchangeRate': exchangeRate,
      'session/floatingPrecision': floatingPrecision,
      'session/currencySymbol': mainCurrency
    }
  ) => {
    const balances = aggregatedBalances as AssetBalance[];
    const totalLiabilities = liabilities as AssetBalance[];

    const assetSum = aggregateTotal(
      balances,
      mainCurrency,
      exchangeRate(mainCurrency),
      floatingPrecision
    );
    const liabilitySum = aggregateTotal(
      totalLiabilities,
      mainCurrency,
      exchangeRate(mainCurrency),
      floatingPrecision
    );
    return assetSum.minus(liabilitySum);
  },

  totalNetWorthUsd: (
    state,
    getters,
    _rootState,
    {
      'balances/aggregatedBalances': aggregatedBalances,
      'balances/liabilities': liabilities
    }
  ) => {
    const balances = aggregatedBalances as AssetBalance[];
    const totalLiabilities = liabilities as AssetBalance[];

    const assetValue = balances.reduce(
      (sum, value) => sum.plus(value.usdValue),
      Zero
    );

    const liabilityValue = totalLiabilities.reduce(
      (sum, value) => sum.plus(value.usdValue),
      Zero
    );

    return assetValue.minus(liabilityValue);
  }
};
