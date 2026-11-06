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
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

const mockNotifyError = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
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
      createAccount({ address: '0x1', label: null, tags: null }, Blockchain.ETH),
    ]);
  });

  /**
   * The guarantee that lets a DB data refresh and a network query overlap without being
   * serialised: whichever carries the older `lastRefreshTs` is discarded, whatever order they land
   * in. Without it the slower one wins and rolls the chain back to stale balances.
   */
  describe('stale payloads', () => {
    const CHAIN = 'gnosis';

    async function resolveCachedFetch(payload: BlockchainBalances): Promise<void> {
      const service = useBalanceProcessingService();
      mockQueryBlockchainBalances.mockResolvedValue(payload);
      await service.handleCachedFetch(
        { addresses: undefined, blockchain: CHAIN, isXpub: false },
        undefined,
      );
    }

    it.each([undefined, 1000])('discards a pre-add cached response with timestamp %s', async (timestamp) => {
      const accounts = useBlockchainAccountsStore();
      accounts.updateAccounts(CHAIN, [createAccount({ address: '0x9', label: null, tags: null }, CHAIN)]);
      const response = deferred<BlockchainBalances>();
      mockQueryBlockchainBalances.mockReturnValue(response.promise);
      const { updateBalances } = useBalancesStore();
      vi.mocked(updateBalances).mockClear();
      const fetching = useBalanceProcessingService().handleCachedFetch(
        { addresses: undefined, blockchain: CHAIN, isXpub: false },
        undefined,
      );
      accounts.invalidateChain(CHAIN);
      response.resolve(timestamp === undefined ? emptyBalances(CHAIN) : balancesAt(CHAIN, timestamp));
      await fetching;
      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('does not let a delayed cache read overwrite a network query even with no timestamp', async () => {
      const accounts = useBlockchainAccountsStore();
      accounts.updateAccounts(CHAIN, [createAccount({ address: '0x9', label: null, tags: null }, CHAIN)]);
      const response = deferred<BlockchainBalances>();
      mockQueryBlockchainBalances.mockReturnValue(response.promise);
      const { updateBalances } = useBalancesStore();
      vi.mocked(updateBalances).mockClear();
      const fetching = useBalanceProcessingService().handleCachedFetch(
        { addresses: undefined, blockchain: CHAIN, isXpub: false },
        undefined,
      );
      useBalanceRefreshState().markNetworkApplied(CHAIN);
      response.resolve(emptyBalances(CHAIN));
      await fetching;
      expect(updateBalances).not.toHaveBeenCalled();
    });

    it.each([undefined, 1000])('rejects a pre-add network response with timestamp %s', async (timestamp) => {
      const accounts = useBlockchainAccountsStore();
      accounts.updateAccounts(CHAIN, [createAccount({ address: '0x9', label: null, tags: null }, CHAIN)]);
      mockRefreshBlockchainBalances.mockResolvedValue({ taskId: 1 });
      const { updateBalances } = useBalancesStore();
      vi.mocked(updateBalances).mockClear();
      const refreshing = useBalanceProcessingService().handleRefresh(
        runTask,
        { addresses: undefined, blockchain: CHAIN, isXpub: false },
      );
      await vi.waitFor(() => expect(pendingTasks.has(1)).toBe(true));
      accounts.invalidateChain(CHAIN);
      pendingTasks.get(1)!.resolve(ok(timestamp === undefined ? emptyBalances(CHAIN) : balancesAt(CHAIN, timestamp)));
      await refreshing;
      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('should ignore a payload older than the chain already holds', async () => {
      useBlockchainAccountsStore().updateAccounts(CHAIN, [
        createAccount({ address: '0x9', label: null, tags: null }, CHAIN),
      ]);
      const { updateBalances } = useBalancesStore();

      await resolveCachedFetch(balancesAt(CHAIN, 3000));
      vi.mocked(updateBalances).mockClear();

      await resolveCachedFetch(balancesAt(CHAIN, 1000));

      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('should ignore an older payload for a multi-word chain whose timestamps arrive camelCased', async () => {
      const chain = 'arbitrum_one';
      useBlockchainAccountsStore().updateAccounts(chain, [
        createAccount({ address: '0x9', label: null, tags: null }, chain),
      ]);
      const { updateBalances } = useBalancesStore();
      const service = useBalanceProcessingService();
      const fetchAt = async (lastRefreshTs: number): Promise<void> => {
        mockQueryBlockchainBalances.mockResolvedValue({ ...balancesAt(chain, lastRefreshTs), lastRefreshTs: { arbitrumOne: lastRefreshTs } });
        await service.handleCachedFetch({ addresses: undefined, blockchain: chain, isXpub: false }, undefined);
      };

      await fetchAt(3000);
      vi.mocked(updateBalances).mockClear();

      await fetchAt(1000);

      expect(updateBalances).not.toHaveBeenCalled();
    });

    it('should accept a payload newer than the chain holds', async () => {
      useBlockchainAccountsStore().updateAccounts(CHAIN, [
        createAccount({ address: '0x9', label: null, tags: null }, CHAIN),
      ]);
      const { updateBalances } = useBalancesStore();

      await resolveCachedFetch(balancesAt(CHAIN, 1000));
      vi.mocked(updateBalances).mockClear();

      await resolveCachedFetch(balancesAt(CHAIN, 3000));

      expect(updateBalances).toHaveBeenCalled();
    });
  });

  describe('pending balances', () => {
    async function refresh(blockchain: string, response: unknown, addresses?: string[]): Promise<void> {
      const taskId = nextTaskId++;
      mockRefreshBlockchainBalances.mockResolvedValue({ taskId });
      const refreshing = useBalanceProcessingService().handleRefresh(runTask, { addresses, blockchain, isXpub: false });
      await vi.waitFor(() => expect(pendingTasks.has(taskId)).toBe(true));
      pendingTasks.get(taskId)!.resolve(ok(response));
      await refreshing;
    }

    it.each([false, true])('should keep an excluded new address pending even if frozen balances are returned: %s', async (frozenBalance) => {
      const accounts = useBlockchainAccountsStore();
      const state = useBalanceRefreshState();
      const settings = useSettingsRepo();
      accounts.updateAccounts(Blockchain.ETH, ['0x1', '0xABC', '0x3'].map(address =>
        createAccount({ address, label: null, tags: null }, Blockchain.ETH)));
      for (const address of ['0x1', '0xABC', '0x3'])
        accounts.markAdded(Blockchain.ETH, address, false);
      settings.updateGeneral({ ...settings.general, disabledChainQueries: { eth: ['0xabc'] } });
      const response = {
        ...emptyBalances(Blockchain.ETH),
        perAccount: {
          eth: Object.fromEntries((frozenBalance ? ['0x1', '0xABC'] : ['0x1']).map(address =>
            [address, { assets: {}, liabilities: {} }])),
        },
      };

      await refresh(Blockchain.ETH, response);

      expect(state.isPending(Blockchain.ETH, '0x1')).toBe(false);
      expect(state.isPending(Blockchain.ETH, '0xABC')).toBe(true);
      expect(state.isPending(Blockchain.ETH, '0x3')).toBe(true); // enabled but absent from the response

      settings.updateGeneral({ ...settings.general, disabledChainQueries: {} });
      await refresh(Blockchain.ETH, {
        ...response,
        perAccount: { eth: { '0xabc': { assets: {}, liabilities: {} } } },
      });
      expect(state.isPending(Blockchain.ETH, '0xABC')).toBe(false);
      expect(state.isPending(Blockchain.ETH, '0x3')).toBe(true);
    });

    it('should not settle any pending address on a fully excluded chain', async () => {
      const accounts = useBlockchainAccountsStore();
      const state = useBalanceRefreshState();
      const settings = useSettingsRepo();
      accounts.markAdded(Blockchain.ETH, '0x1', false);
      settings.updateGeneral({ ...settings.general, disabledChainQueries: { eth: [] } });

      await refresh(Blockchain.ETH, {
        ...emptyBalances(Blockchain.ETH),
        perAccount: { eth: { '0x1': { assets: {}, liabilities: {} } } },
      }, []);

      expect(state.isPending(Blockchain.ETH, '0x1')).toBe(true);
    });

    it('should settle only covered targets from standalone and xpub Bitcoin balances', async () => {
      const accounts = useBlockchainAccountsStore();
      const state = useBalanceRefreshState();
      accounts.updateAccounts(Blockchain.BTC, ['standalone', 'derived', 'untargeted', 'missing'].map(address =>
        createAccount({ address, label: null, tags: null }, Blockchain.BTC)));
      for (const address of ['standalone', 'derived', 'untargeted', 'missing'])
        accounts.markAdded(Blockchain.BTC, address, false);

      await refresh(Blockchain.BTC, {
        ...emptyBalances(Blockchain.BTC),
        perAccount: {
          btc: {
            standalone: {
              standalone: { amount: '0', value: '0' },
              untargeted: { amount: '0', value: '0' },
            },
            xpubs: [{
              addresses: { derived: { amount: '0', value: '0' } },
              derivationPath: null,
              xpub: 'xpub',
            }],
          },
        },
      }, ['STANDALONE', 'derived', 'missing']);

      expect(state.isPending(Blockchain.BTC, 'standalone')).toBe(false);
      expect(state.isPending(Blockchain.BTC, 'derived')).toBe(false);
      expect(state.isPending(Blockchain.BTC, 'untargeted')).toBe(true);
      expect(state.isPending(Blockchain.BTC, 'missing')).toBe(true);
    });

    it('should keep a pending entry newer than the query revision even when covered', async () => {
      const accounts = useBlockchainAccountsStore();
      const state = useBalanceRefreshState();
      accounts.markAdded(Blockchain.ETH, '0x1', false);
      mockRefreshBlockchainBalances.mockResolvedValue({ taskId: 1 });
      const refreshing = useBalanceProcessingService().handleRefresh(
        runTask,
        { blockchain: Blockchain.ETH, isXpub: false },
      );
      await vi.waitFor(() => expect(pendingTasks.has(1)).toBe(true));
      state.markPending(Blockchain.ETH, '0x1', accounts.revisionOf(Blockchain.ETH) + 1);
      pendingTasks.get(1)!.resolve(ok({
        ...emptyBalances(Blockchain.ETH),
        perAccount: { eth: { '0x1': { assets: {}, liabilities: {} } } },
      }));
      await refreshing;

      expect(state.isPending(Blockchain.ETH, '0x1')).toBe(true);
    });
  });

  describe('shouldQuery', () => {
    /**
     * eth2's "accounts" are validators, produced by a backend task rather than an accounts read,
     * so `hasAccounts` is false until that task lands. Gating on it means a balance pass that
     * overtakes the validator fetch skips eth2 entirely — and the backend would have answered:
     * The backend's `ChainsAggregator.query_balances` exempts ETHEREUM_BEACONCHAIN from the same
     * check.
     */
    it('should query eth2 even before its validators have loaded', () => {
      mockIsEth2Enabled.mockReturnValue(true);
      const service = useBalanceProcessingService();

      expect(service.hasAccounts(Blockchain.ETH2)).toBe(false);
      expect(service.shouldQuery(Blockchain.ETH2)).toBe(true);
    });

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
     * The destructive half. Every caller reaches `clearChainBalances` through
     * `!hasAccounts(chain)`, which cannot tell "fetched, genuinely empty" from "not fetched yet".
     * Clearing on unknown *erases* a chain's balances whenever a refresh races the account walk,
     * rather than skipping it — and the balances are gone until something re-queries.
     */
    it('should not erase balances for a chain whose accounts are not loaded yet', () => {
      const service = useBalanceProcessingService();
      const { updateBalances } = useBalancesStore();
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

  it('should not notify when the cached read fails', async () => {
    mockQueryBlockchainBalances.mockRejectedValue(new Error('backend down'));

    const service = useBalanceProcessingService();
    await service.handleCachedFetch(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
      undefined,
    );

    expect(mockNotifyError).not.toHaveBeenCalled();
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

  it('should forget an earlier success when a later refresh fails', async () => {
    const CHAIN = 'base';
    mockRefreshBlockchainBalances.mockImplementation(async () => ({ taskId: nextTaskId++ }));
    useBlockchainAccountsStore().updateAccounts(CHAIN, [
      createAccount({ address: '0x2', label: null, tags: null }, CHAIN),
    ]);

    const service = useBalanceProcessingService();
    const { statusOf } = useTaskOrchestrator();
    const payload = { addresses: undefined, blockchain: CHAIN, isXpub: false };

    const succeeding = service.handleRefresh(runTask, payload);
    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(1);
    });
    pendingTasks.get(1)!.resolve(ok(emptyBalances(CHAIN)));
    await succeeding;

    expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, CHAIN).everCompleted).toBe(true);
    useBlockchainAccountsStore().invalidateChain(CHAIN);
    useBalanceRefreshState().markPending(CHAIN, '0x2', 1);

    pendingTasks.clear();
    const failing = service.handleRefresh(runTask, payload);
    await vi.waitFor(() => {
      expect(pendingTasks.size).toBe(1);
    });
    pendingTasks.get(2)!.resolve(err(Cancelled({ message: 'cancelled' })));
    await failing;

    expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, CHAIN).everCompleted).toBe(false);
    expect(useBalanceRefreshState().isPending(CHAIN, '0x2')).toBe(true);
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
