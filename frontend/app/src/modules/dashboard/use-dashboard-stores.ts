import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';
import { useSetting } from '@/modules/settings/use-setting';

interface UseDashboardStoresReturn {
  currencySymbol: Readonly<Ref<string>>;
  /** Net worth in the dashboard's balance view, the base the tables' percentages are shares of. */
  totalNetWorth: ComputedRef<BigNumber>;
}

export function useDashboardStores(): UseDashboardStoresReturn {
  const currencySymbol = useSetting('currencySymbol');
  const { netWorth } = useBalanceViewData();

  return {
    currencySymbol,
    totalNetWorth: netWorth,
  };
}
