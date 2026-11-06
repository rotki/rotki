import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingRuleMaintenance } from '@/modules/settings/accounting/rule/use-accounting-rule-maintenance';

const deleteAccountingRule = vi.fn(async (): Promise<boolean> => true);
const resetToDefaults = vi.fn(async (): Promise<{ success: boolean } | undefined> => ({ success: true }));

vi.mock('@/modules/settings/api/use-accounting-api', () => ({
  useAccountingApi: (): Record<string, unknown> => ({ deleteAccountingRule }),
}));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({
    exportJSON: vi.fn(),
    resetToDefaults,
  }),
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
  });

  it('should delete a confirmed rule, then reload the table', async () => {
    const { deleteRule, refetch } = createMaintenance();
    await deleteRule(rule);

    expect(deleteAccountingRule).toHaveBeenCalledWith(7);
    expect(refetch).toHaveBeenCalledOnce();
  });

  it('should not reload when the backend reports the rule was not deleted', async () => {
    deleteAccountingRule.mockResolvedValue(false);
    const { deleteRule, refetch } = createMaintenance();
    await deleteRule(rule);

    expect(refetch).not.toHaveBeenCalled();
  });

  it('should keep a failed delete for the table to name instead of throwing', async () => {
    const error = new Error('nope');
    deleteAccountingRule.mockRejectedValue(error);
    const { deleteFailure, deleteRule, refetch } = createMaintenance();
    await deleteRule(rule);

    expect(get(deleteFailure)).toEqual({ error, title: 'accounting_settings.rule.delete_error' });
    expect(refetch).not.toHaveBeenCalled();
  });

  it('should re-count conflicts after a reset, which can create them', async () => {
    const { refetch, refresh, resetRules } = createMaintenance();
    await resetRules();

    expect(refresh).toHaveBeenCalledOnce();
    expect(refetch).not.toHaveBeenCalled();
  });

  it('should not reload when the reset did not happen', async () => {
    resetToDefaults.mockResolvedValue(undefined);
    const { refresh, resetRules } = createMaintenance();
    await resetRules();

    expect(resetToDefaults).toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });
});
