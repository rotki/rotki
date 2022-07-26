import { BigNumber } from '@rotki/common';
import { TimeUnit } from '@rotki/common/lib/settings';
import { timeframes } from '@rotki/common/lib/settings/graphs';
import { NetValue } from '@rotki/common/lib/statistics';
import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import dayjs from 'dayjs';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { setupGeneralBalances } from '@/composables/balances';
import { getSessionState } from '@/composables/session';
import { useSettings } from '@/composables/settings';
import { CURRENCY_USD } from '@/data/currencies';
import { aggregateTotal } from '@/filters';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { bigNumberify, Zero } from '@/utils/bignumbers';

export interface OverallPerformance {
  readonly period: string;
  readonly currency: string;
  readonly percentage: string;
  readonly netWorth: string;
  readonly delta: string;
  readonly up?: boolean;
}

const defaultNetValue = () => ({
  times: [],
  data: []
});

export const useStatisticsStore = defineStore('statistics', () => {
  const netValue = ref<NetValue>(defaultNetValue());

  const { notify } = useNotifications();
  const { frontendSettings, generalSettings } = useSettings();
  const {
    aggregatedBalances,
    liabilities,
    nfBalances,
    nfTotalValue,
    exchangeRate
  } = setupGeneralBalances();

  const totalNetWorth = computed(() => {
    const mainCurrency = get(generalSettings).mainCurrency.tickerSymbol;
    const nftsInNetValue = get(frontendSettings).nftsInNetValue;
    const balances = get(aggregatedBalances);
    const totalLiabilities = get(liabilities);
    const nfbs = get(nfBalances);
    const rate = get(exchangeRate(mainCurrency));
    let nftTotal = Zero;

    if (nftsInNetValue) {
      nftTotal = nfbs.reduce((sum, balance) => {
        return sum.plus(balance.usdPrice.multipliedBy(rate));
      }, Zero);
    }

    const assetSum = aggregateTotal(balances, mainCurrency, rate).plus(
      nftTotal
    );
    const liabilitySum = aggregateTotal(totalLiabilities, mainCurrency, rate);
    return assetSum.minus(liabilitySum);
  });

  const totalNetWorthUsd = computed(() => {
    const balances = get(aggregatedBalances);
    const totalLiabilities = get(liabilities);
    const nftTotal = get(nfTotalValue(true));

    const assetValue = balances.reduce(
      (sum, value) => sum.plus(value.usdValue),
      Zero
    );

    const liabilityValue = totalLiabilities.reduce(
      (sum, value) => sum.plus(value.usdValue),
      Zero
    );

    return assetValue.plus(nftTotal).minus(liabilityValue);
  });

  const overall = computed(() => {
    const {
      mainCurrency: { tickerSymbol: currency },
      uiFloatingPrecision: floatingPrecision
    } = get(generalSettings);
    const rate = get(exchangeRate(currency));

    const timeframe = getSessionState().timeframe;
    const allTimeframes = timeframes((unit, amount) =>
      dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
    );
    const startingDate = allTimeframes[timeframe].startingDate();
    const startingValue: () => BigNumber = () => {
      const data = get(getNetValue(startingDate)).data;
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
    const totalNW = get(totalNetWorth);
    const balanceDelta = totalNW.minus(starting);
    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined = undefined;
    if (balanceDelta.isGreaterThan(0)) {
      up = true;
    } else if (balanceDelta.isLessThan(0)) {
      up = false;
    }

    const delta = balanceDelta.multipliedBy(rate).toFormat(floatingPrecision);

    return {
      period: timeframe,
      currency,
      netWorth: totalNW.toFormat(floatingPrecision),
      delta: delta,
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      up
    };
  });

  const fetchNetValue = async () => {
    try {
      const { nftsInNetValue } = get(frontendSettings);
      set(netValue, await api.queryNetvalueData(nftsInNetValue));
    } catch (e: any) {
      notify({
        title: i18n.t('actions.statistics.net_value.error.title').toString(),
        message: i18n
          .t('actions.statistics.net_value.error.message', {
            message: e.message
          })
          .toString(),
        display: false
      });
    }
  };

  const getNetValue = (startingDate: number) =>
    computed(() => {
      const currency = get(generalSettings).mainCurrency.tickerSymbol;
      const rate = get(exchangeRate(currency));

      const convert = (value: string | number | BigNumber): number => {
        const bigNumber =
          typeof value === 'string' || typeof value === 'number'
            ? bigNumberify(value)
            : value;
        const convertedValue =
          currency === CURRENCY_USD ? bigNumber : bigNumber.multipliedBy(rate);
        return convertedValue.toNumber();
      };

      const { times, data } = get(netValue);
      const nv: NetValue = { times: [], data: [] };
      if (times.length === 0 && data.length === 0) {
        return nv;
      }

      for (let i = 0; i < times.length; i++) {
        const time = times[i];
        if (time < startingDate) {
          continue;
        }
        nv.times.push(time);
        nv.data.push(convert(data[i]));
      }

      const now = Math.floor(new Date().getTime() / 1000);
      const netWorth = get(totalNetWorth).toNumber();
      return {
        times: [...nv.times, now],
        data: [...nv.data, netWorth]
      };
    });

  const reset = () => {
    set(netValue, defaultNetValue());
  };

  return {
    netValue,
    totalNetWorth,
    totalNetWorthUsd,
    overall,
    fetchNetValue,
    getNetValue,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
}
