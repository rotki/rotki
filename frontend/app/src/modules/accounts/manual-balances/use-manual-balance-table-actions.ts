import type { ComputedRef } from 'vue';
import type { ManualBalance, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { omit } from 'es-toolkit';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseManualBalanceTableActionsReturn {
  prepareForEdit: (balance: ManualBalanceWithPrice) => ManualBalance;
  pricesLoading: ComputedRef<boolean>;
  refresh: () => Promise<void>;
  refreshing: ComputedRef<boolean>;
  showDeleteConfirmation: (id: number) => void;
}

export function useManualBalanceTableActions(): UseManualBalanceTableActionsReturn {
  const { deleteManualBalance, fetchManualBalances } = useManualBalances();
  const { show } = useConfirmStore();
  const { t } = useI18n({ useScope: 'global' });

  const { useIsActive } = useTaskCenter();
  const refreshing = useIsActive(ActivityKind.MANUAL_BALANCES);
  const pricesLoading = useIsActive(ActivityKind.PRICES);

  async function refresh(): Promise<void> {
    await fetchManualBalances(true);
  }

  function showDeleteConfirmation(id: number): void {
    show(
      {
        message: t('manual_balances_table.delete_dialog.message'),
        title: t('manual_balances_table.delete_dialog.title'),
      },
      async () => deleteManualBalance(id),
    );
  }

  function prepareForEdit(balance: ManualBalanceWithPrice): ManualBalance {
    return {
      ...omit(balance, ['assetIsMissing', 'price', 'value']),
      asset: balance.assetIsMissing ? '' : balance.asset,
    };
  }

  return {
    prepareForEdit,
    pricesLoading,
    refresh,
    refreshing,
    showDeleteConfirmation,
  };
}
