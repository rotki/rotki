import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';

interface UseDashboardStoresReturn {
  currencySymbol: ComputedRef<string>;
  totalNetWorth: ComputedRef<BigNumber>;
}

export function useDashboardStores(): UseDashboardStoresReturn {
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const statisticsStore = useStatisticsStore();
  const { totalNetWorth } = storeToRefs(statisticsStore);

  return {
    currencySymbol,
    totalNetWorth,
  };
}
