import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingRuleMaintenance } from '@/modules/settings/accounting/rule/use-accounting-rule-maintenance';

const deleteAccountingRule = vi.fn(async (): Promise<boolean> => true);
const resetToDefaults = vi.fn(async (): Promise<{ success: boolean } | undefined> => ({ success: true }));
const setMessage = vi.fn();
/** The confirm store hands the caller's callback to the dialog; the tests run it directly. */
const show = vi.fn(async (_message: unknown, onConfirm: () => Promise<void> | void): Promise<void> => {
  await onConfirm();
});

vi.mock('@/modules/settings/api/use-accounting-api', () => ({
  useAccountingApi: (): Record<string, unknown> => ({ deleteAccountingRule }),
}));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({
    exportJSON: vi.fn(),
    resetToDefaults,
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): Ref<boolean> => ref(false) }),
}));

const rule: AccountingRuleEntry = {
  accountingTreatment: null,
  countCostBasisPnl: { value: false },
  countEntireAmountSpend: { value: false },
  counterparty: null,
  eventSubtype: 'fee',
  eventType: 'spend',
  identifier: 7,
  taxable: { value: false },
};

function createMaintenance(): ReturnType<typeof useAccountingRuleMaintenance> & {
  refetch: ReturnType<typeof vi.fn>;
  refresh: ReturnType<typeof vi.fn>;
} {
  const refetch = vi.fn(async (): Promise<void> => {});
  const refresh = vi.fn(async (): Promise<void> => {});
  return { ...useAccountingRuleMaintenance({ refetch, refresh }), refetch, refresh };
}

describe('useAccountingRuleMaintenance', () => {
  beforeEach(() => {
    deleteAccountingRule.mockClear().mockResolvedValue(true);
    resetToDefaults.mockClear().mockResolvedValue({ success: true });
    setMessage.mockClear();
    show.mockClear();
  });

  it('should confirm before deleting, then reload the table', async () => {
    const { confirmDelete, refetch } = createMaintenance();
    confirmDelete(rule);
    await vi.waitFor(() => expect(refetch).toHaveBeenCalledOnce());

    expect(show).toHaveBeenCalledOnce();
    expect(deleteAccountingRule).toHaveBeenCalledWith(7);
  });

  it('should not reload when the backend reports the rule was not deleted', async () => {
    deleteAccountingRule.mockResolvedValue(false);
    const { confirmDelete, refetch } = createMaintenance();
    confirmDelete(rule);
    await vi.waitFor(() => expect(deleteAccountingRule).toHaveBeenCalled());

    expect(refetch).not.toHaveBeenCalled();
  });

  it('should report a failed delete instead of throwing', async () => {
    deleteAccountingRule.mockRejectedValue(new Error('nope'));
    const { confirmDelete, refetch } = createMaintenance();
    confirmDelete(rule);
    await vi.waitFor(() => expect(setMessage).toHaveBeenCalledOnce());

    expect(refetch).not.toHaveBeenCalled();
  });

  it('should re-count conflicts after a reset, which can create them', async () => {
    const { confirmReset, refetch, refresh } = createMaintenance();
    confirmReset();
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());

    expect(refetch).not.toHaveBeenCalled();
  });

  it('should not reload when the reset did not happen', async () => {
    resetToDefaults.mockResolvedValue(undefined);
    const { confirmReset, refresh } = createMaintenance();
    confirmReset();
    await vi.waitFor(() => expect(resetToDefaults).toHaveBeenCalled());

    expect(refresh).not.toHaveBeenCalled();
  });
});
