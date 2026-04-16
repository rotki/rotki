import type { CommonQueryStatusData, FailedHistoricalAssetPriceResponse } from '@rotki/common';
import type { StatsPriceQueryData } from '@/modules/messaging/types';

export const useHistoricCachePriceStore = defineStore('prices/historic-cache', () => {
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
