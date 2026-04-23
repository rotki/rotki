import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChainName: vi.fn((chain: string) => computed(() => chain)),
    }),
  };
});

const mockQueryBlockchainBalances = vi.fn();
const mockRefreshBlockchainBalances = vi.fn();

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: (...args: unknown[]) => mockQueryBlockchainBalances(...args),
    refreshBlockchainBalances: (...args: unknown[]) => mockRefreshBlockchainBalances(...args),
    queryXpubBalances: vi.fn(),
  }),
}));

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

const pendingTasks = new Map<number, Deferred<{ success: true; result: unknown }>>();
let nextTaskId = 1;

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: vi.fn().mockImplementation(async (taskFn: () => Promise<{ taskId: number }>) => {
      const { taskId } = await taskFn();
      const d = deferred<{ success: true; result: unknown }>();
      pendingTasks.set(taskId, d);
      return d.promise;
    }),
  }),
}));

const { useBalanceProcessingService } = await import('@/modules/balances/services/use-balance-processing-service');

function emptyBalances(blockchain: string): unknown {
  return {
    perAccount: { [blockchain]: {} },
    totals: { assets: {}, liabilities: {} },
  };
}

describe('useBalanceProcessingService', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pendingTasks.clear();
    nextTaskId = 1;
    mockQueryBlockchainBalances.mockReset();
    mockRefreshBlockchainBalances.mockReset();

    const { updateAccounts } = useBlockchainAccountsStore();
    updateAccounts(Blockchain.ETH, [
      createAccount({ address: '0x1', label: null, tags: null }, { chain: Blockchain.ETH, nativeAsset: 'ETH' }),
    ]);
  });

  it('should flip hasCachedData when the cached GET resolves, before refresh POST completes', async () => {
    mockQueryBlockchainBalances.mockImplementation(async () => ({ taskId: nextTaskId++ }));
    mockRefreshBlockchainBalances.mockImplementation(async () => ({ taskId: nextTaskId++ }));

    const service = useBalanceProcessingService();
    const { hasCachedData, isRefreshing } = useBalanceStatus(Blockchain.ETH);

    const cachedPromise = service.handleCachedFetch(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
      undefined,
    );
    const refreshPromise = service.handleRefresh(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
    );

    // wait for both api calls to have registered their tasks
    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(2);
    });

    expect(get(hasCachedData)).toBe(false);
    expect(get(isRefreshing)).toBe(true);

    // resolve the cached GET task first (taskId 1)
    pendingTasks.get(1)!.resolve({ success: true, result: emptyBalances(Blockchain.ETH) });
    await cachedPromise;

    expect(get(hasCachedData)).toBe(true);
    expect(get(isRefreshing)).toBe(true); // refresh POST still in flight

    // resolve the refresh POST task
    pendingTasks.get(2)!.resolve({ success: true, result: emptyBalances(Blockchain.ETH) });
    await refreshPromise;

    expect(get(hasCachedData)).toBe(true);
    expect(get(isRefreshing)).toBe(false);
  });

  it('should clear isRefreshing even when the refresh POST fails', async () => {
    mockRefreshBlockchainBalances.mockImplementation(async () => ({ taskId: nextTaskId++ }));

    const service = useBalanceProcessingService();
    const refreshState = useBalanceRefreshState();
    const isEthRefreshing = refreshState.useIsRefreshing(Blockchain.ETH);

    const refreshPromise = service.handleRefresh(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
    );

    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(1);
    });
    expect(get(isEthRefreshing)).toBe(true);

    pendingTasks.get(1)!.resolve({
      success: false,
      message: 'cancelled',
      cancelled: true,
      backendCancelled: false,
      skipped: false,
    } as never);
    await refreshPromise;

    expect(get(isEthRefreshing)).toBe(false);
  });
});
