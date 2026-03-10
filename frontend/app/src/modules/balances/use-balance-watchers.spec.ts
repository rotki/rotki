import type { EffectScope } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceSource, type BalanceValueThreshold } from '@/types/settings/frontend-settings';

const fetchManualBalances = vi.fn(async (): Promise<void> => {});
const fetchConnectedExchangeBalances = vi.fn(async (): Promise<void> => {});
const fetchBlockchainBalances = vi.fn(async (): Promise<void> => {});
const removeIgnoredAssets = vi.fn();

const mockBalanceValueThreshold = ref<BalanceValueThreshold>({});
const mockIgnoredAssets = ref<string[]>([]);

vi.mock('@shared/utils', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    startPromise: vi.fn((promise: Promise<unknown>): void => {
      promise.catch((): void => {});
    }),
  };
});

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: vi.fn().mockReturnValue({
    fetchManualBalances,
  }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: vi.fn().mockReturnValue({
    fetchConnectedExchangeBalances,
  }),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({
    fetchBlockchainBalances,
  }),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    removeIgnoredAssets,
  }),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: vi.fn().mockReturnValue({
    ignoredAssets: mockIgnoredAssets,
  }),
}));

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn().mockReturnValue({
    balanceValueThreshold: mockBalanceValueThreshold,
  }),
}));

describe('useBalanceWatchers', () => {
  let scope: EffectScope;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    scope = effectScope();

    set(mockBalanceValueThreshold, {});
    set(mockIgnoredAssets, []);
  });

  afterEach(() => {
    scope.stop();
  });

  it('should refetch manual balances when manual threshold changes', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    scope.run(() => {
      useBalanceWatchers();
    });

    set(mockBalanceValueThreshold, { [BalanceSource.MANUAL]: '100' });
    await nextTick();

    expect(fetchManualBalances).toHaveBeenCalledOnce();
    expect(fetchManualBalances).toHaveBeenCalledWith(true);
    expect(fetchConnectedExchangeBalances).not.toHaveBeenCalled();
    expect(fetchBlockchainBalances).not.toHaveBeenCalled();
  });

  it('should refetch exchange balances when exchange threshold changes', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    scope.run(() => {
      useBalanceWatchers();
    });

    set(mockBalanceValueThreshold, { [BalanceSource.EXCHANGES]: '50' });
    await nextTick();

    expect(fetchConnectedExchangeBalances).toHaveBeenCalledOnce();
    expect(fetchConnectedExchangeBalances).toHaveBeenCalledWith(false);
    expect(fetchManualBalances).not.toHaveBeenCalled();
    expect(fetchBlockchainBalances).not.toHaveBeenCalled();
  });

  it('should refetch blockchain balances when blockchain threshold changes', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    scope.run(() => {
      useBalanceWatchers();
    });

    set(mockBalanceValueThreshold, { [BalanceSource.BLOCKCHAIN]: '200' });
    await nextTick();

    expect(fetchBlockchainBalances).toHaveBeenCalledOnce();
    expect(fetchManualBalances).not.toHaveBeenCalled();
    expect(fetchConnectedExchangeBalances).not.toHaveBeenCalled();
  });

  it('should not refetch when threshold stays the same', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    set(mockBalanceValueThreshold, { [BalanceSource.MANUAL]: '100' });
    await nextTick();

    scope.run(() => {
      useBalanceWatchers();
    });
    vi.clearAllMocks();

    set(mockBalanceValueThreshold, { [BalanceSource.MANUAL]: '100' });
    await nextTick();

    expect(fetchManualBalances).not.toHaveBeenCalled();
    expect(fetchConnectedExchangeBalances).not.toHaveBeenCalled();
    expect(fetchBlockchainBalances).not.toHaveBeenCalled();
  });

  it('should refetch blockchain balances when ignored assets are removed', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    set(mockIgnoredAssets, ['asset-a', 'asset-b']);
    await nextTick();

    scope.run(() => {
      useBalanceWatchers();
    });
    vi.clearAllMocks();

    set(mockIgnoredAssets, ['asset-a']);
    await nextTick();

    expect(fetchBlockchainBalances).toHaveBeenCalledOnce();
  });

  it('should call removeIgnoredAssets when assets are added to ignored list', async () => {
    const { useBalanceWatchers } = await import('./use-balance-watchers');

    set(mockIgnoredAssets, ['asset-a']);
    await nextTick();

    scope.run(() => {
      useBalanceWatchers();
    });
    vi.clearAllMocks();

    const updatedAssets = ['asset-a', 'asset-b', 'asset-c'];
    set(mockIgnoredAssets, updatedAssets);
    await nextTick();

    expect(removeIgnoredAssets).toHaveBeenCalledOnce();
    expect(removeIgnoredAssets).toHaveBeenCalledWith(updatedAssets);
    expect(fetchBlockchainBalances).not.toHaveBeenCalled();
  });
});
