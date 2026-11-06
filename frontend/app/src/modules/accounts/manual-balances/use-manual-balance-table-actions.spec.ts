import { describe, expect, it, vi } from 'vitest';
import { useManualBalanceTableActions } from '@/modules/accounts/manual-balances/use-manual-balance-table-actions';

const { deleteManualBalance } = vi.hoisted(() => ({
  deleteManualBalance: vi.fn<(id: number) => Promise<boolean>>(),
}));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: (): { deleteManualBalance: typeof deleteManualBalance } => ({ deleteManualBalance }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', async () => {
  const { computed } = await import('vue');
  return { usePriceRefresh: (): Record<string, unknown> => ({ refreshing: computed<boolean>(() => false) }) };
});

describe('useManualBalanceTableActions', () => {
  it('should ask the delete question the table has always asked', () => {
    const { deleteConfirm } = useManualBalanceTableActions();

    expect(deleteConfirm).toEqual({
      message: 'manual_balances_table.delete_dialog.message',
      title: 'manual_balances_table.delete_dialog.title',
    });
  });

  it('should delete the balance it is given', async () => {
    deleteManualBalance.mockResolvedValue(true);
    const { deleteFailure, deleteRow } = useManualBalanceTableActions();

    await deleteRow(4);

    expect(deleteManualBalance).toHaveBeenCalledWith(4);
    expect(get(deleteFailure)).toBeUndefined();
  });

  it('should keep a failed delete for the table to name', async () => {
    const error = new Error('locked');
    deleteManualBalance.mockRejectedValue(error);
    const { deleteFailure, deleteRow } = useManualBalanceTableActions();

    await deleteRow(4);

    expect(get(deleteFailure)).toEqual({ failure: error, title: 'actions.balances.manual_delete.error.title' });
  });
});
