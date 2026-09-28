import type { EffectScope } from 'vue';
import { ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingRows } from '@/modules/shell/action-center/use-accounting-rows';

const { count, recount } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports -- vi.hoisted runs before the import graph is evaluated, so ref has to be required here
  const { ref: vueRef } = require('vue');
  return { count: vueRef(0), recount: vi.fn() };
});

vi.mock('@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count', () => ({
  useAccountingRuleConflictsCount: (): object => ({ count, refresh: recount }),
}));

let scope: EffectScope | undefined;

function accountingRows(): ReturnType<typeof useAccountingRows> {
  scope = effectScope();
  const result = scope.run(() => useAccountingRows());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-accounting-rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recount.mockResolvedValue(ok(0));
    set(count, 0);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should count the conflicting accounting rules', () => {
    const { rows } = accountingRows();
    set(count, 2);

    const [row] = get(rows);
    expect(row.id).toBe('accounting-rule-conflicts');
    expect(row.count).toBe(2);
  });

  it('should open the accounting rules page with its resolve dialog up', () => {
    const [row] = get(accountingRows().rows);

    expect(row.target).toEqual({ kind: 'route', to: { name: '/settings/accounting/', query: { resolveConflicts: 'true' } } });
  });

  it('should open the page alone when cleared, since there is nothing to resolve', () => {
    const [row] = get(accountingRows().rows);

    expect(row.checkTarget).toEqual({ kind: 'route', to: { name: '/settings/accounting/' } });
  });

  it('should re-read the conflicts on refresh', async () => {
    await accountingRows().refresh();

    expect(recount).toHaveBeenCalledOnce();
  });
});
