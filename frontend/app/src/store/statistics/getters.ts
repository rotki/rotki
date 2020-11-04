import { default as BigNumber } from 'bignumber.js';
import { aggregateTotal } from '@/filters';
import { NetValue } from '@/services/types-api';
import { StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { bigNumberify } from '@/utils/bignumbers';

interface StatisticsGetters {
  netValue: (startingDate: number) => NetValue;
  totalNetWorth: BigNumber;
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
    { 'balances/exchangeRate': exchangeRate, 'session/currency': currency }
  ) => (startingDate: number): NetValue => {
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
      netValue.data.push(
        bigNumberify(data[i])
          .multipliedBy(exchangeRate(currency.ticker_symbol))
          .toNumber()
      );
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
      'balances/exchangeRate': exchangeRate,
      'session/floatingPrecision': floatingPrecision,
      'session/currency': currency
    }
  ) => {
    const mainCurrency = currency.ticker_symbol;
    return aggregateTotal(
      aggregatedBalances,
      mainCurrency,
      exchangeRate(mainCurrency),
      floatingPrecision
    );
  }
};
