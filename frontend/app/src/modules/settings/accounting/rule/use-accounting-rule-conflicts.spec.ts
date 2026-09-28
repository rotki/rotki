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

const { count, refresh } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    count: ref<number>(0),
    refresh: vi.fn<() => Promise<Result<number, RequestError>>>(),
  };
});

vi.mock('@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count', () => ({
  useAccountingRuleConflictsCount: (): Record<string, unknown> => ({ count, refresh }),
}));

const failure = err(RequestFailed({ cause: new Error('boom'), message: 'boom' }));

describe('useAccountingRuleConflicts', () => {
  beforeEach(() => {
    query = {};
    set(count, 0);
    replace.mockClear();
    refresh.mockReset().mockResolvedValue(ok(0));
  });

  it('should count what the action center counts, so the page and the row agree', async () => {
    set(count, 3);
    const { checkConflicts, conflictsNumber, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(refresh).toHaveBeenCalledOnce();
    expect(get(conflictsNumber)).toBe(3);
    expect(get(modelConflictsDialogOpen)).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });

  it('should open the dialog when the route asks for it, as the action center row does', async () => {
    query = { resolveConflicts: 'true' };
    refresh.mockResolvedValue(ok(2));
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

  it('should open the dialog on a failed count when the route asks, so its table can say why', async () => {
    query = { resolveConflicts: 'true' };
    refresh.mockResolvedValue(failure);
    const { checkConflicts, modelConflictsDialogOpen } = useAccountingRuleConflicts();
    await checkConflicts();

    expect(get(modelConflictsDialogOpen)).toBe(true);
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });
});
