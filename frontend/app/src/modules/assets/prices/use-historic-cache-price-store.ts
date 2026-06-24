import type { BigNumber, CommonQueryStatusData, FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { StatsPriceQueryData } from '@/modules/core/messaging/types';
import { createItemCacheStorage } from '@/modules/core/common/use-item-cache';

export const useHistoricCachePriceStore = defineStore('prices/historic-cache', () => {
  // App-lifetime cache storage for historic prices; the fetch/debounce/LRU logic
  // lives in useHistoricPriceCache, which binds to this so the cache survives
  // navigation (composable teardown) instead of being wiped at zero subscribers.
  const historicStorage = createItemCacheStorage<BigNumber>();
  const statsPriceQueryStatus = shallowRef<Record<string, StatsPriceQueryData>>({});
  const historicalPriceStatus = shallowRef<CommonQueryStatusData>();
  const historicalDailyPriceStatus = shallowRef<CommonQueryStatusData>();
  const failedDailyPrices = shallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({});
  const resolvedFailedDailyPrices = shallowRef<Record<string, number[]>>({});

  const getProtocolStatsPriceQueryStatus = (counterparty: string): ComputedRef<StatsPriceQueryData | undefined> => computed(() => get(statsPriceQueryStatus)[counterparty]);

  function setStatsPriceQueryStatus(data: StatsPriceQueryData): void {
    const currentData = {
      ...get(statsPriceQueryStatus),
    };

    currentData[data.counterparty] = data;

    set(statsPriceQueryStatus, currentData);
  }

  function resetProtocolStatsPriceQueryStatus(counterparty: string): void {
    const currentData = {
      ...get(statsPriceQueryStatus),
    };

    delete currentData[counterparty];

    set(statsPriceQueryStatus, currentData);
  }

  function setHistoricalDailyPriceStatus(status: CommonQueryStatusData): void {
    set(historicalDailyPriceStatus, status);
  }

  function setHistoricalPriceStatus(status: CommonQueryStatusData): void {
    set(historicalPriceStatus, status);
  }

  return {
    failedDailyPrices,
    getProtocolStatsPriceQueryStatus,
    historicStorage,
    historicalDailyPriceStatus,
    historicalPriceStatus,
    resetProtocolStatsPriceQueryStatus,
    resolvedFailedDailyPrices,
    setHistoricalDailyPriceStatus,
    setHistoricalPriceStatus,
    setStatsPriceQueryStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot));
