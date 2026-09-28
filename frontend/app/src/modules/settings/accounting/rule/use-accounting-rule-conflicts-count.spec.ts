import { err, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { RequestCancelled, type RequestError, RequestFailed } from '@/modules/core/api/request-result';

const { getAccountingRulesConflicts, logError } = vi.hoisted(() => ({
  getAccountingRulesConflicts: vi.fn<() => Promise<Result<{ total: number }, RequestError>>>(),
  logError: vi.fn(),
}));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({ getAccountingRulesConflicts }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: logError },
}));

const cause = new Error('boom');

let scope: ReturnType<typeof effectScope> | undefined;

/**
 * Imports the composable into a fresh module registry, inside a scope the test stops.
 *
 * @remarks
 * `useAccountingRuleConflictsCount` is a `createSharedComposable` singleton, so without the reset one
 * test's count would be the next one's starting value.
 */
async function setup(): Promise<ReturnType<typeof import('@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count')['useAccountingRuleConflictsCount']>> {
  vi.resetModules();
  const { useAccountingRuleConflictsCount } = await import('@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count');
  scope = effectScope();
  const result = scope.run(() => useAccountingRuleConflictsCount());
  assert(result);
  return result;
}

describe('modules/settings/accounting/rule/use-accounting-rule-conflicts-count', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should count the conflicts from the total, asking for a single entry', async () => {
    getAccountingRulesConflicts.mockResolvedValue(ok({ total: 4 }));
    const { count, refresh } = await setup();

    expect(await refresh()).toEqual(ok(4));
    expect(get(count)).toBe(4);
    expect(getAccountingRulesConflicts).toHaveBeenCalledWith({ limit: 1, offset: 0 });
  });

  it('should keep the last known count when a recount fails, rather than claiming none', async () => {
    getAccountingRulesConflicts
      .mockResolvedValueOnce(ok({ total: 3 }))
      .mockResolvedValueOnce(err(RequestFailed({ cause, message: 'boom' })));
    const { count, refresh } = await setup();

    await refresh();
    const failed = await refresh();

    assert(!failed.ok);
    expect(get(count)).toBe(3);
    expect(logError).toHaveBeenCalledExactlyOnceWith(cause);
  });

  it('should not log a recount that was cancelled', async () => {
    getAccountingRulesConflicts.mockResolvedValue(err(RequestCancelled({ message: 'logout' })));
    const { refresh } = await setup();

    await refresh();

    expect(getAccountingRulesConflicts).toHaveBeenCalledOnce();
    expect(logError).not.toHaveBeenCalled();
  });

  it('should go back to zero when the user logs out', async () => {
    getAccountingRulesConflicts.mockResolvedValue(ok({ total: 2 }));
    const store = useSessionAuthStore();
    store.logged = true;
    const { count, refresh } = await setup();
    await refresh();

    store.logged = false;
    await nextTick();

    expect(get(count)).toBe(0);
  });
});
