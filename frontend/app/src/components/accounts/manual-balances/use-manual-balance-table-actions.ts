import type { ComputedRef } from 'vue';
import type { ManualBalance, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { omit } from 'es-toolkit';
import { useSectionStatus } from '@/composables/status';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { Section } from '@/modules/common/status';
import { useConfirmStore } from '@/store/confirm';

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

  const { isLoading: refreshing } = useSectionStatus(Section.MANUAL_BALANCES);
  const { isLoading: pricesLoading } = useSectionStatus(Section.PRICES);

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
