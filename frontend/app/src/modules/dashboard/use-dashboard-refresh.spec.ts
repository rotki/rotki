import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { RefreshSource } from '@/modules/balances/refresh/core/refresh-types';
import { Module } from '@/modules/core/common/modules';
import {
  DashboardExtraSource,
  type DashboardRefreshAction,
  DashboardRefreshKind,
} from '@/modules/dashboard/dashboard-refresh-action';
import { useDashboardRefresh } from '@/modules/dashboard/use-dashboard-refresh';

const mocks = vi.hoisted(() => ({
  fetchPools: vi.fn<(refresh?: boolean) => Promise<void>>(async () => {}),
  redetectAndRefreshAll: vi.fn<() => Promise<void>>(async () => {}),
  refreshAll: vi.fn<() => Promise<void>>(async () => {}),
  refreshAllPrices: vi.fn<() => Promise<void>>(async () => {}),
  refreshNonFungibleBalances: vi.fn<(userInitiated?: boolean) => Promise<void>>(async () => {}),
  refreshSourceAndPrices: vi.fn<(source: string) => Promise<void>>(async () => {}),
}));

const activeModules = ref<string[]>([]);

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: (): typeof mocks => mocks,
}));

vi.mock('@/modules/balances/nft/use-nft-balances', () => ({
  useNftBalances: (): Record<string, unknown> => ({ refreshNonFungibleBalances: mocks.refreshNonFungibleBalances }),
}));

vi.mock('@/modules/dashboard/liquidity-pools/use-pool-data-fetching', () => ({
  usePoolDataFetching: (): Record<string, unknown> => ({ fetch: mocks.fetchPools }),
}));

vi.mock('@/modules/settings/use-setting', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/settings/use-setting')>();
  return {
    ...original,
    useSetting: (key: string): unknown => (key === 'activeModules' ? activeModules : Reflect.apply(original.useSetting, undefined, [key])),
  };
});

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
    set(activeModules, []);
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

  it('should refresh the NFTs or the pools on their own, with no price refresh after', async () => {
    const { refresh } = useDashboardRefresh();

    await refresh({ kind: DashboardRefreshKind.EXTRA_SOURCE, source: DashboardExtraSource.NFTS });
    expect(mocks.refreshNonFungibleBalances).toHaveBeenCalledExactlyOnceWith(true);
    expect(mocks.fetchPools).not.toHaveBeenCalled();

    await refresh({ kind: DashboardRefreshKind.EXTRA_SOURCE, source: DashboardExtraSource.POOLS });
    expect(mocks.fetchPools).toHaveBeenCalledExactlyOnceWith(true);
    expect(mocks.refreshAllPrices).not.toHaveBeenCalled();
    expect(mocks.refreshSourceAndPrices).not.toHaveBeenCalled();
  });

  it('should offer the NFTs and the pools only while their modules are enabled', () => {
    const { extraSources } = useDashboardRefresh();
    expect(get(extraSources)).toEqual([]);

    set(activeModules, [Module.NFTS, Module.SUSHISWAP]);
    expect(get(extraSources)).toEqual([DashboardExtraSource.NFTS, DashboardExtraSource.POOLS]);

    set(activeModules, [Module.UNISWAP]);
    expect(get(extraSources)).toEqual([DashboardExtraSource.POOLS]);
  });
});
