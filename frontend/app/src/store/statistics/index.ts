import type { TaskMeta } from '@/types/task';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import { usePremium } from '@/composables/premium';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useNotificationsStore } from '@/store/notifications';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import { CURRENCY_USD, type SupportedCurrency } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';
import { type BigNumber, type HistoricalAssetPricePayload, HistoricalAssetPriceResponse, type NetValue, One, type TimeFramePeriod, timeframes, TimeUnit, Zero } from '@rotki/common';
import dayjs from 'dayjs';

function defaultNetValue(): NetValue {
  return {
    data: [],
    times: [],
  };
}

interface Overall {
  currency: SupportedCurrency;
  delta: string;
  netWorth: string;
  percentage: string;
  period: TimeFramePeriod;
  up?: boolean;
}

export const useStatisticsStore = defineStore('statistics', () => {
  const netValue = ref<NetValue>(defaultNetValue());

  const { t } = useI18n();

  const { nftsInNetValue } = storeToRefs(useFrontendSettingsStore());
  const { notify } = useNotificationsStore();
  const { currencySymbol, floatingPrecision } = storeToRefs(useGeneralSettingsStore());
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { useExchangeRate } = usePriceUtils();
  const { assetName } = useAssetInfoRetrieval();
  const { failedDailyPrices, resolvedFailedDailyPrices } = storeToRefs(useHistoricCachePriceStore());
  const premium = usePremium();

  const api = useStatisticsApi();
  const { balances, liabilities } = useAggregatedBalances();
  const { awaitTask } = useTaskStore();
  const { logged } = storeToRefs(useSessionAuthStore());

  const calculateTotalValue = (includeNft = false): ComputedRef<BigNumber> => computed<BigNumber>(() => {
    const aggregatedBalances = get(balances());
    const totalLiabilities = get(liabilities());
    const nftTotal = includeNft ? get(nonFungibleTotalValue) : 0;
    const assetValue = aggregatedBalances.reduce((sum, value) => sum.plus(value.usdValue), Zero);
    const liabilityValue = totalLiabilities.reduce((sum, value) => sum.plus(value.usdValue), Zero);

    return assetValue.plus(nftTotal).minus(liabilityValue);
  });

  const totalNetWorth = computed<BigNumber>(() => {
    const mainCurrency = get(currencySymbol);
    const rate = get(useExchangeRate(mainCurrency)) ?? One;
    return get(calculateTotalValue(get(nftsInNetValue))).multipliedBy(rate);
  });

  const overall = computed<Overall>(() => {
    const currency = get(currencySymbol);
    const rate = get(useExchangeRate(currency)) ?? One;
    const selectedTimeframe = get(timeframe);
    const allTimeframes = timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix());
    const startingDate = allTimeframes[selectedTimeframe].startingDate();

    const startingValue: () => BigNumber = () => {
      const data = get(getNetValue(startingDate)).data;
      let start = data[0];
      if (start.isZero()) {
        for (let i = 1; i < data.length; i++) {
          if (data[i].gt(0)) {
            start = data[i];
            break;
          }
        }
      }
      return start;
    };

    const starting = startingValue();
    const totalNW = get(totalNetWorth);
    const balanceDelta = totalNW.minus(starting);
    const percentage = balanceDelta.div(starting).multipliedBy(100);

    let up: boolean | undefined;
    if (balanceDelta.isGreaterThan(0))
      up = true;
    else if (balanceDelta.isLessThan(0))
      up = false;

    const floatPrecision = get(floatingPrecision);
    const delta = balanceDelta.multipliedBy(rate).toFormat(floatPrecision);

    return {
      currency,
      delta,
      netWorth: totalNW.toFormat(floatPrecision),
      percentage: percentage.isFinite() ? percentage.toFormat(2) : '-',
      period: selectedTimeframe,
      up,
    };
  });

  const totalNetWorthUsd = calculateTotalValue(true);

  function getNetValue(startingDate: number): ComputedRef<NetValue> {
    return computed<NetValue>(() => {
      const currency = get(currencySymbol);
      const rate = get(useExchangeRate(currency)) ?? One;

      const convert = (value: BigNumber): BigNumber => (currency === CURRENCY_USD ? value : value.multipliedBy(rate));

      const { data, times } = get(netValue);

      const now = Math.floor(Date.now() / 1000);
      const netWorth = get(totalNetWorth);

      if (times.length === 0 && data.length === 0) {
        const oneDayTimestamp = 24 * 60 * 60;

        return {
          data: [Zero, netWorth],
          times: [now - oneDayTimestamp, now],
        };
      }

      const nv: NetValue = { data: [], times: [] };

      for (const [i, time] of times.entries()) {
        if (time < startingDate)
          continue;

        nv.times.push(time);
        nv.data.push(convert(data[i]));
      }

      return {
        data: [...nv.data, netWorth],
        times: [...nv.times, now],
      };
    });
  }

  const fetchNetValue = async (): Promise<void> => {
    try {
      set(netValue, await api.queryNetValueData(get(nftsInNetValue)));
    }
    catch (error: any) {
      notify({
        display: false,
        message: t('actions.statistics.net_value.error.message', {
          message: error.message,
        }),
        title: t('actions.statistics.net_value.error.title'),
      });
    }
  };

  const resetFailedStates = (asset: string, parsed: HistoricalAssetPriceResponse, excludeTimestamps: number[]): void => {
    const { noPricesTimestamps, rateLimitedPricesTimestamps } = parsed;

    const failedState = { ...get(failedDailyPrices) };
    const resolvedState = { ...get(resolvedFailedDailyPrices) };

    if ((noPricesTimestamps.length === 0 && excludeTimestamps.length === 0) && rateLimitedPricesTimestamps.length === 0) {
      if (failedState[asset]) {
        const updatedFailedPrices = { ...failedState };
        delete updatedFailedPrices[asset];
        set(failedDailyPrices, updatedFailedPrices);
      }
      if (resolvedState[asset]) {
        delete resolvedState[asset];
        set(resolvedFailedDailyPrices, resolvedState);
      }
    }
    else {
      set(failedDailyPrices, {
        ...failedState,
        [asset]: {
          noPricesTimestamps: noPricesTimestamps.length > 0 ? noPricesTimestamps : excludeTimestamps,
          rateLimitedPricesTimestamps,
        },
      });
    }
  };

  const fetchHistoricalAssetPrice = async (payload: HistoricalAssetPricePayload): Promise<HistoricalAssetPriceResponse> => {
    try {
      const asset = payload.asset;
      const failedState = { ...get(failedDailyPrices) };
      const resolvedState = { ...get(resolvedFailedDailyPrices) };
      const failedTimestamps = failedState[asset]?.noPricesTimestamps || [];
      const resolvedTimestamps = resolvedState[asset] || [];

      const excludeTimestamps
        = failedTimestamps.filter(timestamp => !resolvedTimestamps.includes(timestamp));

      const taskType = TaskType.FETCH_DAILY_HISTORIC_PRICE;
      const { taskId } = await api.queryHistoricalAssetPrices({
        ...payload,
        excludeTimestamps,
      });
      const { result } = await awaitTask<HistoricalAssetPriceResponse, TaskMeta>(taskId, taskType, {
        description: t('actions.balances.historic_fetch_price.daily.task.detail', {
          asset: get(assetName(payload.asset)),
        }),
        title: t('actions.balances.historic_fetch_price.daily.task.title'),
      });

      const parsed = HistoricalAssetPriceResponse.parse(result);
      resetFailedStates(asset, parsed, excludeTimestamps);
      return parsed;
    }
    catch (error: any) {
      logger.error(error);
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.historic_fetch_price.daily.error.message'),
          title: t('actions.balances.historic_fetch_price.daily.task.title'),
        });
      }

      return {
        noPricesTimestamps: [],
        prices: {},
        rateLimitedPricesTimestamps: [],
      };
    }
  };

  watch(premium, async () => {
    if (get(logged))
      await fetchNetValue();
  });

  return {
    fetchHistoricalAssetPrice,
    fetchNetValue,
    getNetValue,
    netValue,
    overall,
    totalNetWorth,
    totalNetWorthUsd,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useStatisticsStore, import.meta.hot));
