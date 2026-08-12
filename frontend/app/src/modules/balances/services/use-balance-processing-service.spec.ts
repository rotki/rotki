import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import { Blockchain } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { Cancelled, type TaskError } from '@/modules/core/tasks/task-result';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

const mockIsEth2Enabled = vi.fn((): boolean => true);

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: vi.fn(() => ({ isEth2Enabled: mockIsEth2Enabled })),
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

const pendingTasks = new Map<number, Deferred<Result<unknown, TaskError>>>();
let nextTaskId = 1;

// The service takes its runner from the activity that called it, so the spec passes this one in
// rather than faking the handler module.
const runTask = vi.fn().mockImplementation(async (taskFn: () => Promise<{ taskId: number }>) => {
  const { taskId } = await taskFn();
  const d = deferred<Result<unknown, TaskError>>();
  pendingTasks.set(taskId, d);
  return d.promise;
});

const { useBalanceProcessingService } = await import('@/modules/balances/services/use-balance-processing-service');

function balancesAt(blockchain: string, lastRefreshTs: number): BlockchainBalances {
  return {
    lastRefreshTs: { [blockchain]: lastRefreshTs },
    perAccount: { [blockchain]: {} },
    totals: { assets: {}, liabilities: {} },
  };
}

function emptyBalances(blockchain: string): BlockchainBalances {
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

  /**
   * ⭐ The guarantee that lets a DB data refresh and a network query overlap without being
   * serialised: whichever carries the older `lastRefreshTs` is discarded, whatever order they land
   * in. Without it the slower one wins and rolls the chain back to stale balances.
   */
  describe('stale payloads', () => {
    // ⚠️ A chain of its own, not ETH. The orchestrator is a `createSharedComposable`, so its
    // completion ledger survives `setActivePinia` and leaks between tests — marking ETH complete
    // here makes a later test see `hasCachedData` already true.
    const CHAIN = 'gnosis';

    async function resolveCachedFetch(payload: BlockchainBalances): Promise<void> {
      const service = useBalanceProcessingService();
      mockQueryBlockchainBalances.mockResolvedValue(payload);
      await service.handleCachedFetch(
        { addresses: undefined, blockchain: CHAIN, isXpub: false },
        undefined,
      );
    }

    it('should ignore a payload older than the chain already holds', async () => {
      useBlockchainAccountsStore().updateAccounts(CHAIN, [
        createAccount({ address: '0x9', label: null, tags: null }, { chain: CHAIN, nativeAsset: 'ETH' }),
      ]);
      const { updateBalances } = useBalancesStore();

      await resolveCachedFetch(balancesAt(CHAIN, 3000));
      vi.mocked(updateBalances).mockClear();

      await resolveCachedFetch(balancesAt(CHAIN, 1000));

      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('should accept a payload newer than the chain holds', async () => {
      useBlockchainAccountsStore().updateAccounts(CHAIN, [
        createAccount({ address: '0x9', label: null, tags: null }, { chain: CHAIN, nativeAsset: 'ETH' }),
      ]);
      const { updateBalances } = useBalancesStore();

      await resolveCachedFetch(balancesAt(CHAIN, 1000));
      vi.mocked(updateBalances).mockClear();

      await resolveCachedFetch(balancesAt(CHAIN, 3000));

      expect(updateBalances).toHaveBeenCalled();
    });
  });

  describe('shouldQuery', () => {
    /**
     * 🔴 eth2's "accounts" are validators, produced by a backend task rather than an accounts read,
     * so `hasAccounts` is false until that task lands. Gating on it means a balance pass that
     * overtakes the validator fetch skips eth2 entirely — and the backend would have answered:
     * `aggregator.py:727` exempts ETHEREUM_BEACONCHAIN from the same check.
     */
    it('should query eth2 even before its validators have loaded', () => {
      mockIsEth2Enabled.mockReturnValue(true);
      const service = useBalanceProcessingService();

      expect(service.hasAccounts(Blockchain.ETH2)).toBe(false);
      expect(service.shouldQuery(Blockchain.ETH2)).toBe(true);
    });

    // The backend's other precondition: with the module off there is nothing to query.
    it('should not query eth2 when the module is disabled', () => {
      mockIsEth2Enabled.mockReturnValue(false);
      const service = useBalanceProcessingService();

      expect(service.shouldQuery(Blockchain.ETH2)).toBe(false);
    });

    it('should still require accounts for every other chain', () => {
      mockIsEth2Enabled.mockReturnValue(true);
      const service = useBalanceProcessingService();

      expect(service.shouldQuery('optimism')).toBe(false);
      expect(service.shouldQuery(Blockchain.ETH)).toBe(true);
    });
  });

  describe('clearChainBalances', () => {
    /**
     * A refresh that races the accounts fetch sees every chain as empty. Recording a completion
     * there marked the chain "ever loaded" with no balances, so the initial-loading state dropped
     * while the real data was still on its way.
     */
    it('should not record a completion for a chain whose accounts are not loaded yet', () => {
      const service = useBalanceProcessingService();
      const { statusOf } = useTaskOrchestrator();

      // `optimism` was never written by the accounts fetch — its set is unknown, not empty.
      service.clearChainBalances('optimism');

      expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, 'optimism').everCompleted).toBe(false);
    });

    it('should record a completion for a chain fetched with no accounts', () => {
      const service = useBalanceProcessingService();
      const { statusOf } = useTaskOrchestrator();
      const { updateAccounts } = useBlockchainAccountsStore();

      // The accounts fetch writes the key even when the chain has none: known, and genuinely empty.
      updateAccounts('optimism', []);
      service.clearChainBalances('optimism');

      expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, 'optimism').everCompleted).toBe(true);
    });

    /**
     * 🔴 The destructive half. Every caller reaches `clearChainBalances` through
     * `!hasAccounts(chain)`, which cannot tell "fetched, genuinely empty" from "not fetched yet".
     * Clearing on unknown *erases* a chain's balances whenever a refresh races the account walk,
     * rather than skipping it — and the balances are gone until something re-queries.
     */
    it('should not erase balances for a chain whose accounts are not loaded yet', () => {
      const service = useBalanceProcessingService();
      const { updateBalances } = useBalancesStore();
      // ⚠️ The spy comes from the module mock factory, so unlike the pinia stores (recreated in
      // `beforeEach`) it carries the calls every earlier test in this file made through it.
      vi.mocked(updateBalances).mockClear();

      // `zksync_lite` was never written by the accounts fetch — unknown, not empty.
      service.clearChainBalances('zksync_lite');

      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('should erase balances for a chain known to have no accounts', () => {
      const service = useBalanceProcessingService();
      const { updateAccounts } = useBlockchainAccountsStore();
      const { updateBalances } = useBalancesStore();

      updateAccounts('scroll', []);
      service.clearChainBalances('scroll');

      expect(updateBalances).toHaveBeenCalledWith('scroll', {
        perAccount: {},
        totals: { assets: {}, liabilities: {} },
      });
    });
  });

  it('should flip hasCachedData when the cached GET resolves, before refresh POST completes', async () => {
    const cachedBalances = deferred<BlockchainBalances>();
    mockQueryBlockchainBalances.mockReturnValue(cachedBalances.promise);
    mockRefreshBlockchainBalances.mockImplementation(async () => ({ taskId: nextTaskId++ }));

    const service = useBalanceProcessingService();
    const { hasCachedData, isRefreshing } = useBalanceStatus(Blockchain.ETH);

    const cachedPromise = service.handleCachedFetch(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
      undefined,
    );
    const refreshPromise = service.handleRefresh(
      runTask,
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
    );

    // Only the refresh registers a backend task. The cached GET is a direct request.
    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(1);
    });

    expect(get(hasCachedData)).toBe(false);
    expect(get(isRefreshing)).toBe(true);

    cachedBalances.resolve(emptyBalances(Blockchain.ETH));
    await cachedPromise;

    expect(get(hasCachedData)).toBe(true);
    expect(get(isRefreshing)).toBe(true); // refresh POST still in flight

    pendingTasks.get(1)!.resolve(ok(emptyBalances(Blockchain.ETH)));
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
      runTask,
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
    );

    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(1);
    });
    expect(get(isEthRefreshing)).toBe(true);

    pendingTasks.get(1)!.resolve(err(Cancelled({ message: 'cancelled' })));
    await refreshPromise;

    expect(get(isEthRefreshing)).toBe(false);
  });
});
