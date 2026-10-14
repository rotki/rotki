import type { ComputedRef } from 'vue';
import type { ManualBalance, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { omit } from 'es-toolkit';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseManualBalanceTableActionsReturn {
  prepareForEdit: (balance: ManualBalanceWithPrice) => ManualBalance;
  pricesLoading: ComputedRef<boolean>;
  showDeleteConfirmation: (id: number) => void;
}

export function useManualBalanceTableActions(): UseManualBalanceTableActionsReturn {
  const { deleteManualBalance } = useManualBalances();
  const { show } = useConfirmStore();
  const { t } = useI18n({ useScope: 'global' });

  const { refreshing: pricesLoading } = usePriceRefresh();

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
    showDeleteConfirmation,
  };
}
