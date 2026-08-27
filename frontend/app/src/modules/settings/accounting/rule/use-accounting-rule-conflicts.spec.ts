import type { LocationQuery } from 'vue-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingRuleConflicts } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts';

const replace = vi.fn(async (): Promise<void> => {});
let query: LocationQuery = {};

vi.mock('vue-router', () => ({
  useRoute: (): { query: LocationQuery } => ({ get query(): LocationQuery {
    return query;
  } }),
  useRouter: (): { replace: typeof replace } => ({ replace }),
}));

const getAccountingRulesConflicts = vi.fn(async (): Promise<{ total: number }> => ({ total: 0 }));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({ getAccountingRulesConflicts }),
}));

describe('useAccountingRuleConflicts', () => {
  beforeEach(() => {
    query = {};
    replace.mockClear();
    getAccountingRulesConflicts.mockClear().mockResolvedValue({ total: 0 });
  });

  it('should count the conflicts without opening the dialog', async () => {
    getAccountingRulesConflicts.mockResolvedValue({ total: 3 });
    const { checkConflicts, conflictsNumber, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(conflictsNumber)).toBe(3);
    expect(get(modelConflictsDialogOpen)).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });

  it('should open the dialog when the route asks for it, as the notification link does', async () => {
    query = { resolveConflicts: 'true' };
    getAccountingRulesConflicts.mockResolvedValue({ total: 2 });
    const { checkConflicts, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(modelConflictsDialogOpen)).toBe(true);
    // Consumed, so a reload does not reopen it.
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });

  it('should consume the request but stay closed when nothing conflicts, landing on the page', async () => {
    query = { resolveConflicts: 'true' };
    const { checkConflicts, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(modelConflictsDialogOpen)).toBe(false);
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });
});
