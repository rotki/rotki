import { AssetBalance, BigNumber } from '@rotki/common';
import { TimeUnit } from '@rotki/common/lib/settings';
import { TimeFramePeriod, timeframes } from '@rotki/common/lib/settings/graphs';
import dayjs from 'dayjs';
import { aggregateTotal } from '@/filters';
import { NetValue } from '@/services/types-api';
import { NonFungibleBalance } from '@/store/balances/types';
import { OverallPerformance, StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { bigNumberify, Zero } from '@/utils/bignumbers';

interface StatisticsGetters {
  netValue: (startingDate: number) => NetValue;
  totalNetWorth: BigNumber;
  totalNetWorthUsd: BigNumber;
  overall: OverallPerformance;
}

export const getters: Getters<
  StatisticsState,
  StatisticsGetters,
  RotkehlchenState,
  any
> = {
  netValue:
    (
      state,
      getters,
      _rootState,
      {
        'balances/exchangeRate': exchangeRate,
        'session/currencySymbol': currency
      }
    ) =>
    (startingDate: number): NetValue => {
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

      const now = Math.floor(new Date().getTime() / 1000);
      const netWorth = getters.totalNetWorth.toNumber();
      return {
        times: netWorth > 0 ? [...netValue.times, now] : [...netValue.times],
        data: netWorth > 0 ? [...netValue.data, netWorth] : [...netValue.data]
      };
    },

  totalNetWorth: (
    state,
    getters,
    _rootState,
    {
      'balances/aggregatedBalances': aggregatedBalances,
      'balances/liabilities': liabilities,
      'balances/nfBalances': nfBalances,
      'balances/exchangeRate': exchangeRate,
      'session/currencySymbol': mainCurrency
    }
  ) => {
    const balances = aggregatedBalances as AssetBalance[];
    const totalLiabilities = liabilities as AssetBalance[];
    const nfbs = nfBalances as NonFungibleBalance[];
    const rate = exchangeRate(mainCurrency);
    let nftTotal = Zero;

    if (_rootState.settings?.nftsInNetValue) {
      nftTotal = nfbs.reduce((sum, balance) => {
        return sum.plus(balance.usdPrice.multipliedBy(rate));
      }, Zero);
    }

    const assetSum = aggregateTotal(
      balances,
      mainCurrency,
      exchangeRate(mainCurrency)
    ).plus(nftTotal);
    const liabilitySum = aggregateTotal(
      totalLiabilities,
      mainCurrency,
      exchangeRate(mainCurrency)
    );
    return assetSum.minus(liabilitySum);
  },

  totalNetWorthUsd: (
    state,
    getters,
    _rootState,
    {
      'balances/aggregatedBalances': aggregatedBalances,
      'balances/liabilities': liabilities,
      'balances/nfTotalValue': nfTotalValue
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

    return assetValue.plus(nfTotalValue).minus(liabilityValue);
  },
  overall: (
    state,
    { totalNetWorth, netValue },
    rootState,
    {
      'balances/exchangeRate': exchangeRate,
      'session/currencySymbol': currency,
      'session/floatingPrecision': floatingPrecision
    }
  ) => {
    const timeframe = rootState.session!!.timeframe as TimeFramePeriod;
    const allTimeframes = timeframes((unit, amount) =>
      dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
    );
    const startingDate = allTimeframes[timeframe].startingDate();
    const startingValue: () => BigNumber = () => {
      const data = netValue(startingDate).data;
      let start = data[0];
      if (start === 0) {
        for (let i = 1; i < data.length; i++) {
          if (data[i] > 0) {
            start = data[i];
            break;
          }
        }
      }
      return bigNumberify(start);
    };

    const starting = startingValue();
    const balanceDelta = totalNetWorth.minus(starting);
    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined = undefined;
    if (balanceDelta.isGreaterThan(0)) {
      up = true;
    } else if (balanceDelta.isLessThan(0)) {
      up = false;
    }

    const delta = balanceDelta
      .multipliedBy(exchangeRate(currency))
      .toFormat(floatingPrecision);

    return {
      period: timeframe,
      currency,
      netWorth: totalNetWorth.toFormat(floatingPrecision),
      delta: delta,
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      up
    };
  }
};
