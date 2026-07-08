import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseDashboardStoresReturn {
  currencySymbol: Readonly<Ref<string>>;
  totalNetWorth: ComputedRef<BigNumber>;
}

export function useDashboardStores(): UseDashboardStoresReturn {
  const currencySymbol = useSetting('currencySymbol');
  const statisticsStore = useStatisticsStore();
  const { totalNetWorth } = storeToRefs(statisticsStore);

  return {
    currencySymbol,
    totalNetWorth,
  };
}
