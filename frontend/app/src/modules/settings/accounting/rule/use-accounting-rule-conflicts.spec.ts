import type { LocationQuery } from 'vue-router';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type RequestError, RequestFailed } from '@/modules/core/api/request-result';
import { useAccountingRuleConflicts } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts';

const replace = vi.fn(async (): Promise<void> => {});
let query: LocationQuery = {};

vi.mock('vue-router', () => ({
  useRoute: (): { query: LocationQuery } => ({ get query(): LocationQuery {
    return query;
  } }),
  useRouter: (): { replace: typeof replace } => ({ replace }),
}));

const getAccountingRulesConflicts = vi.fn(async (): Promise<Result<{ total: number }, RequestError>> => ok({ total: 0 }));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({ getAccountingRulesConflicts }),
}));

const failure = err(RequestFailed({ cause: new Error('boom'), message: 'boom' }));

describe('useAccountingRuleConflicts', () => {
  beforeEach(() => {
    query = {};
    replace.mockClear();
    getAccountingRulesConflicts.mockClear().mockResolvedValue(ok({ total: 0 }));
  });

  it('should count the conflicts without opening the dialog', async () => {
    getAccountingRulesConflicts.mockResolvedValue(ok({ total: 3 }));
    const { checkConflicts, conflictsNumber, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(conflictsNumber)).toBe(3);
    expect(get(modelConflictsDialogOpen)).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });

  it('should open the dialog when the route asks for it, as the notification link does', async () => {
    query = { resolveConflicts: 'true' };
    getAccountingRulesConflicts.mockResolvedValue(ok({ total: 2 }));
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

  it('should keep the last known count when a recount fails, rather than claiming none', async () => {
    getAccountingRulesConflicts.mockResolvedValueOnce(ok({ total: 3 }));
    const { checkConflicts, conflictsNumber } = useAccountingRuleConflicts();
    await checkConflicts();

    getAccountingRulesConflicts.mockResolvedValueOnce(failure);
    await checkConflicts();

    expect(get(conflictsNumber)).toBe(3);
  });

  it('should open the dialog on a failed count when the route asks, so its table can say why', async () => {
    query = { resolveConflicts: 'true' };
    getAccountingRulesConflicts.mockResolvedValue(failure);
    const { checkConflicts, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(modelConflictsDialogOpen)).toBe(true);
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });
});
