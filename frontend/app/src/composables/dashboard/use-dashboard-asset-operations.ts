import type { AssetBalanceWithPrice } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { Routes } from '@/router/routes';
import { isEvmNativeToken } from '@/types/asset';
import { DashboardTableType } from '@/types/settings/frontend-settings';

interface UseDashboardAssetOperationsReturn {
  expanded: Ref<AssetBalanceWithPrice[]>;
  isRowExpandable: (row: AssetBalanceWithPrice) => boolean;
  redirectToManualBalance: (item: AssetBalanceWithPrice) => void;
}

export function useDashboardAssetOperations(
  tableType: MaybeRefOrGetter<DashboardTableType>,
): UseDashboardAssetOperationsReturn {
  const router = useRouter();
  const expanded = ref<AssetBalanceWithPrice[]>([]);

  function redirectToManualBalance(item: AssetBalanceWithPrice): void {
    const type = toValue(tableType);
    if ([DashboardTableType.ASSETS, DashboardTableType.LIABILITIES].includes(type)) {
      startPromise(router.push({
        path: `${Routes.BALANCES_MANUAL.toString()}/${type.toLowerCase()}`,
        query: {
          asset: item.asset,
        },
      }));
    }
  }

  function isRowExpandable(row: AssetBalanceWithPrice): boolean {
    const hasBreakdown = Boolean(row.breakdown);
    const isNativeToken = isEvmNativeToken(row.asset);
    const hasMultipleProtocols = (row.perProtocol?.length ?? 0) > 1;

    return hasBreakdown || isNativeToken || hasMultipleProtocols;
  }

  return {
    expanded,
    isRowExpandable,
    redirectToManualBalance,
  };
}
