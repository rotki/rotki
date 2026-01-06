import type { ComputedRef } from 'vue';
import type { ManualBalance, ManualBalanceWithPrice } from '@/types/manual-balances';
import { omit } from 'es-toolkit';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useConfirmStore } from '@/store/confirm';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

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
  const { isLoading } = useStatusStore();
  const { t } = useI18n({ useScope: 'global' });

  const refreshing = isLoading(Section.MANUAL_BALANCES);
  const pricesLoading = isLoading(Section.PRICES);

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
      ...omit(balance, ['assetIsMissing', 'usdPrice', 'value']),
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
