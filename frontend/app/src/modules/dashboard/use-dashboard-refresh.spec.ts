import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { RefreshSource } from '@/modules/balances/refresh/core/refresh-types';
import { type DashboardRefreshAction, DashboardRefreshKind } from '@/modules/dashboard/dashboard-refresh-action';
import { useDashboardRefresh } from '@/modules/dashboard/use-dashboard-refresh';

const mocks = vi.hoisted(() => ({
  redetectAndRefreshAll: vi.fn<() => Promise<void>>(async () => {}),
  refreshAll: vi.fn<() => Promise<void>>(async () => {}),
  refreshAllPrices: vi.fn<() => Promise<void>>(async () => {}),
  refreshSourceAndPrices: vi.fn<(source: string) => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: (): typeof mocks => mocks,
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): unknown => ref(false) }),
}));

vi.mock('@/modules/banks/use-bank-data', () => ({
  useBankData: (): Record<string, unknown> => ({ banks: computed(() => []) }),
}));

describe('useDashboardRefresh', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it.each([
    { action: { kind: DashboardRefreshKind.BALANCES }, expected: 'refreshAll' },
    { action: { kind: DashboardRefreshKind.REDETECT }, expected: 'redetectAndRefreshAll' },
    { action: { kind: DashboardRefreshKind.PRICES }, expected: 'refreshAllPrices' },
  ] satisfies { action: DashboardRefreshAction; expected: keyof typeof mocks }[])(
    'should run only $expected for $action.kind',
    async ({ action, expected }) => {
      await useDashboardRefresh().refresh(action);

      for (const [name, fn] of Object.entries(mocks))
        expect(fn, name).toHaveBeenCalledTimes(name === expected ? 1 : 0);
    },
  );

  it('should refresh the chosen source, then prices', async () => {
    await useDashboardRefresh().refresh({ kind: DashboardRefreshKind.SOURCE, source: RefreshSource.BANKS });

    expect(mocks.refreshSourceAndPrices).toHaveBeenCalledExactlyOnceWith(RefreshSource.BANKS);
    expect(mocks.refreshAll).not.toHaveBeenCalled();
  });

  it('should offer no source when nothing is connected', () => {
    expect(useDashboardRefresh().sources.value).toEqual([]);
  });
});
