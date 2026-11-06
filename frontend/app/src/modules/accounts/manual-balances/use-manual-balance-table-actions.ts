import type { ComputedRef, Ref } from 'vue';
import type { ManualBalance, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { omit } from 'es-toolkit';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

interface UseManualBalanceTableActionsReturn {
  /** For `RowActions`' `delete-confirm`, so the row's delete button asks before it emits. */
  deleteConfirm: RowDeleteQuestion;
  /** Deletes a balance the user already confirmed. */
  deleteRow: (id: number) => Promise<void>;
  /** Why the last delete failed, until the next one starts. */
  deleteFailure: Readonly<Ref<NamedFailure | undefined>>;
  prepareForEdit: (balance: ManualBalanceWithPrice) => ManualBalance;
  pricesLoading: ComputedRef<boolean>;
}

export function useManualBalanceTableActions(): UseManualBalanceTableActionsReturn {
  const { deleteManualBalance } = useManualBalances();
  const { t } = useI18n({ useScope: 'global' });

  const { refreshing: pricesLoading } = usePriceRefresh();

  const deleteConfirm = {
    message: t('manual_balances_table.delete_dialog.message'),
    title: t('manual_balances_table.delete_dialog.title'),
  };

  const { deleteRow, failure: deleteFailure } = useTableRowDeletion<number>({
    deleteItem: async id => deleteManualBalance(id),
    failureTitle: () => t('actions.balances.manual_delete.error.title'),
  });

  function prepareForEdit(balance: ManualBalanceWithPrice): ManualBalance {
    return {
      ...omit(balance, ['assetIsMissing', 'price', 'value']),
      asset: balance.assetIsMissing ? '' : balance.asset,
    };
  }

  return {
    deleteConfirm,
    deleteFailure,
    deleteRow,
    prepareForEdit,
    pricesLoading,
  };
}
