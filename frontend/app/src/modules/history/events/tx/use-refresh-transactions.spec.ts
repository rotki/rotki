import type { RefreshTransactionsParams } from './types';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { SeededAccount } from '@/modules/history/use-tx-query-status-store';
import flushPromises from 'flush-promises';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { ActivityKind, makeActivityId, type WorkStatus } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { useRefreshTransactions } from './use-refresh-transactions';

const mockOnHistoryStarted = vi.fn();
const mockOnHistoryFinished = vi.fn();

vi.mock('@/modules/session/use-scheduler-state', () => ({
  useSchedulerState: vi.fn(() => ({
    onHistoryStarted: mockOnHistoryStarted,
    onHistoryFinished: mockOnHistoryFinished,
  })),
}));

const mockEvmAccounts: ChainAddress[] = [
  { address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' },
  { address: '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', chain: 'optimism' },
];

const mockBitcoinAccounts: ChainAddress[] = [
  { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' },
];

const mockExchanges: Exchange[] = [
  { location: 'kraken', name: 'Kraken1' },
  { location: 'binance', name: 'Binance1' },
];

const mockTxQueryStatusStore = {
  initializeQueryStatus: vi.fn<(accounts: SeededAccount[], options?: { extend?: boolean }) => void>(),
  resetQueryStatus: vi.fn(),
  stopSyncing: vi.fn(),
};

const mockEventsQueryStatusStore = {
  initializeQueryStatus: vi.fn(),
  resetQueryStatus: vi.fn(),
  stopSyncing: vi.fn(),
};

const mockDisabledChains = {
  filterAccounts: vi.fn((accounts: ChainAddress[]) => accounts),
};

const mockHistoryTransactionAccounts = {
  getAllAccounts: vi.fn(() => [...mockEvmAccounts, ...mockBitcoinAccounts]),
  getTransactionTypeFromChain: vi.fn((chain: string): TransactionChainType =>
    chain === 'btc' ? TransactionChainType.BITCOIN : TransactionChainType.EVM,
  ),
};

// Novelty now comes from the completion ledger, so the spec states which per-account work has been
// attempted instead of relying on a side effect of the first refresh.
const attempted = new Set<string>();

vi.mock('@/modules/task-center/use-native-task', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-native-task')>();
  return {
    ...actual,
    useNativeTask: vi.fn(() => {
      const real = actual.useNativeTask();
      return {
        ...real,
        // The umbrella's own status comes from the real orchestrator, so the re-entrancy guard and
        // the "has history ever loaded" check are exercised for real rather than pinned to a
        // constant. Only the per-account/per-exchange ledger novelty detection reads is faked.
        statusOf: vi.fn((kind: string, ...parts: string[]) => {
          if (kind === actual.ActivityKind.HISTORY_SYNC)
            return real.statusOf(actual.ActivityKind.HISTORY_SYNC, ...parts);

          return {
            active: false,
            everCompleted: false,
            lastOutcome: attempted.has([kind, ...parts].join(':')) ? 'complete' : undefined,
            pending: false,
            running: false,
          };
        }),
      };
    }),
  };
});

const HISTORY_SYNC_ID = makeActivityId(ActivityKind.HISTORY_SYNC);

function historySyncStatus(): WorkStatus {
  return useTaskOrchestrator().statusOf(ActivityKind.HISTORY_SYNC);
}

/**
 * `submitTask` resolves off the producer's own promise, one tick before the orchestrator marks the
 * activity terminal. So a caller that awaits a refresh and immediately submits another still sees
 * the umbrella active and takes the re-entrancy branch. Flush so each refresh below asserts real
 * behaviour rather than passing because the previous one looks like it is still running.
 */
async function settleRefresh(): Promise<void> {
  await flushPromises();
}

function markAttempted(): void {
  attempted.add('tx-sync:eth:0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');
  attempted.add('tx-sync:optimism:0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199');
  attempted.add('tx-sync:btc:bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh');
  attempted.add('exchange-events:kraken:Kraken1');
  attempted.add('exchange-events:binance:Binance1');
}

const mockUndecodedTransactionsStatus = {
  fetchUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue(undefined),
};

const mockDecodingStatusStore = {
  resetDecodingSyncProgress: vi.fn(),
  resumeDecodingSyncProgress: vi.fn(),
  resetUndecodedTransactionsStatus: vi.fn(),
  stopDecodingSyncProgress: vi.fn(),
};

type SyncOutcomes = Promise<Result<void, TaskError>[]>;

/**
 * Records what it synced *and* returns an outcome per chain: the drain reads the completion ledger
 * and the umbrella settles on its children, so a bare `vi.fn()` breaks every test in this file.
 *
 * Named so `beforeEach` can restore it. `failEverything` below uses `mockResolvedValue`, which
 * `vi.clearAllMocks()` does not undo, and an unrestored failure turns every later test's first
 * refresh into a failed one.
 */
async function defaultSyncByChains(accounts: ChainAddress[]): SyncOutcomes {
  for (const account of accounts)
    attempted.add(`tx-sync:${account.chain}:${account.address}`);
  return accounts.map(() => ok(undefined));
}

async function defaultQueryExchanges(exchanges: Exchange[] = []): SyncOutcomes {
  for (const exchange of exchanges)
    attempted.add(`exchange-events:${exchange.location}:${exchange.name}`);
  return exchanges.map(() => ok(undefined));
}

const mockTransactionSync = {
  syncTransactionsByChains: vi.fn<(accounts: ChainAddress[], showProgress: boolean, parent?: string) => SyncOutcomes>(
    defaultSyncByChains,
  ),
};

const mockSupportedChains = {
  isDecodableChains: vi.fn((chain: string) => ['eth', 'optimism', 'polygon_pos', 'solana'].includes(chain)),
};

const mockRefreshHandlers = {
  // Same contract as the sync mock above: settling is what makes an exchange stop being novel.
  queryAllExchangeEvents: vi.fn(defaultQueryExchanges),
  queryOnlineEvent: vi.fn().mockResolvedValue(ok(undefined)),
  resetOnlineWarnings: vi.fn(),
};

const mockExchangeData = {
  isSameExchange: (a: Exchange, b: Exchange): boolean => a.location === b.location && a.name === b.name,
  syncingExchanges: ref<Exchange[]>(mockExchanges),
};

/** Every kind of child reports a failure, so the umbrella has no success to settle on. */
function failEverything(): void {
  const failure = err(TaskFailed({ message: 'backend unreachable' }));
  mockTransactionSync.syncTransactionsByChains.mockResolvedValue([failure]);
  mockRefreshHandlers.queryAllExchangeEvents.mockResolvedValue([failure]);
  mockRefreshHandlers.queryOnlineEvent.mockResolvedValue(failure);
}

/** The inverse of {@link failEverything}, for the second half of a recovery test. */
function succeedEverything(): void {
  mockTransactionSync.syncTransactionsByChains.mockResolvedValue([ok(undefined)]);
  mockRefreshHandlers.queryAllExchangeEvents.mockResolvedValue([ok(undefined)]);
  mockRefreshHandlers.queryOnlineEvent.mockResolvedValue(ok(undefined));
}

vi.mock('./use-history-transaction-accounts', () => ({
  useHistoryTransactionAccounts: vi.fn(() => mockHistoryTransactionAccounts),
}));

vi.mock('@/modules/settings/general/disabled-chain-queries/use-disabled-chains', () => ({
  useDisabledChains: vi.fn(() => mockDisabledChains),
}));

vi.mock('./use-undecoded-transactions-status', () => ({
  useUndecodedTransactionsStatus: vi.fn(() => mockUndecodedTransactionsStatus),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => mockDecodingStatusStore),
}));

vi.mock('./use-transaction-sync', () => ({
  useTransactionSync: vi.fn(() => mockTransactionSync),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => mockSupportedChains),
}));

vi.mock('./use-refresh-handlers', () => ({
  useRefreshHandlers: vi.fn(() => mockRefreshHandlers),
}));

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: vi.fn(() => mockExchangeData),
}));

vi.mock('@/modules/history/use-tx-query-status-store', () => ({
  useTxQueryStatusStore: vi.fn(() => mockTxQueryStatusStore),
}));

vi.mock('@/modules/history/use-events-query-status-store', () => ({
  useEventsQueryStatusStore: vi.fn(() => mockEventsQueryStatusStore),
}));

describe('useRefreshTransactions', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    scope = effectScope();

    // The orchestrator is a shared singleton, so its completion ledger would otherwise leak the
    // umbrella's `everCompleted` from one test into the next.
    useTaskOrchestrator().reset();

    vi.clearAllMocks();
    attempted.clear();

    mockTransactionSync.syncTransactionsByChains.mockImplementation(defaultSyncByChains);
    mockRefreshHandlers.queryAllExchangeEvents.mockImplementation(defaultQueryExchanges);
    mockRefreshHandlers.queryOnlineEvent.mockResolvedValue(ok(undefined));
    mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts]);
    mockDisabledChains.filterAccounts.mockImplementation((accounts: ChainAddress[]) => accounts);
    set(mockExchangeData.syncingExchanges, mockExchanges);
  });

  afterEach(() => {
    scope.stop();
  });

  describe('basic refresh flow', () => {
    // The account store fills one chain at a time. Scoping the sync off a snapshot taken mid-read
    // drops whatever has not arrived, and the sync then reports complete over chains it never
    // covered. Waiting for the read is what makes the scope whole.
    it('should wait for a running account read before taking its scope', async () => {
      const { useAccountLoadState } = await import('@/modules/accounts/use-account-load-state');
      let finishRead = (): void => {};
      const read = new Promise<void>((resolve) => {
        finishRead = resolve;
      });
      const tracked = useAccountLoadState().track(read);

      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts]);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const refreshing = refreshTransactions();
      await Promise.resolve();

      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts]);
      finishRead();
      await tracked;

      await refreshing;
      await settleRefresh();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining([...mockEvmAccounts, ...mockBitcoinAccounts]),
        expect.anything(),
        HISTORY_SYNC_ID,
      );
    });

    it('should perform full refresh when called without parameters', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();
      await settleRefresh();

      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
      expect(mockDecodingStatusStore.resetUndecodedTransactionsStatus).toHaveBeenCalled();
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalled();
      expect(historySyncStatus().everCompleted).toBe(true);
      expect(historySyncStatus().active).toBe(false);
    });

    it('should skip refresh when history already loaded and no new accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });

    it('should show sync progress on first load', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(expect.anything(), true, HISTORY_SYNC_ID);
    });

    it('should not show sync progress on subsequent loads without novelty', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions({ userInitiated: true });

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(expect.anything(), false, HISTORY_SYNC_ID);
    });
  });

  describe('account-specific refresh', () => {
    it('should refresh only specified accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const specificAccounts = [mockEvmAccounts[0]];

      await refreshTransactions({
        payload: { accounts: specificAccounts },
        userInitiated: true, // Ensure it bypasses any "already refreshed" logic
      });

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        specificAccounts,
        true, // shouldShowSyncProgress is true because history has not loaded yet
        HISTORY_SYNC_ID,
      );
    });

    it('should not query exchanges when only accounts are specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: mockEvmAccounts },
      });

      expect(mockRefreshHandlers.queryAllExchangeEvents).not.toHaveBeenCalled();
      expect(mockEventsQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('exchange refresh', () => {
    it('should refresh exchanges when exchanges are specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { exchanges: mockExchanges },
      });

      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(mockExchanges, { extend: false });
      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(mockExchanges, HISTORY_SYNC_ID);
    });

    it('should refresh all connected exchanges in full refresh', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith(mockExchanges, HISTORY_SYNC_ID);
      expect(mockEventsQueryStatusStore.initializeQueryStatus).toHaveBeenCalled();
    });
  });

  describe('new account detection', () => {
    it('should refresh already loaded history when a new account is detected', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      attempted.delete('tx-sync:eth:0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
    });
  });

  describe('new exchange detection', () => {
    it('should refresh already loaded history when a new exchange is detected', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      attempted.delete('exchange-events:kraken:Kraken1');
      mockRefreshHandlers.queryAllExchangeEvents.mockClear();

      await refreshTransactions();

      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalled();
    });
  });

  describe('concurrent refresh handling', () => {
    it('should sync an account added while a refresh was running', async () => {
      vi.useFakeTimers();

      // An account the in-flight refresh does not cover. It becomes tracked mid-refresh, which is
      // what makes it novel: the drain asks the completion ledger which tracked accounts have never
      // been attempted, rather than keeping a set of deferred keys.
      const addedMidRefresh: ChainAddress = { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', chain: 'eth' };

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts, addedMidRefresh]);

      await refreshTransactions({
        payload: { accounts: [addedMidRefresh] },
      });

      await firstRefresh;

      await vi.advanceTimersByTimeAsync(150);
      // The drain re-enters asynchronously; without settling it here the tail of that refresh lands
      // in the next test and looks like a spurious drain there.
      await settleRefresh();

      // Twice: the first refresh over every account, then the drain over the late arrival alone.
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledTimes(2);
      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenLastCalledWith([addedMidRefresh], expect.anything(), HISTORY_SYNC_ID);

      vi.useRealTimers();
    });

    it('should extend the progress panel on the drained wave instead of replacing it', async () => {
      vi.useFakeTimers();

      const addedMidRefresh: ChainAddress = { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', chain: 'eth' };

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts, addedMidRefresh]);

      await refreshTransactions({ payload: { accounts: [addedMidRefresh] } });
      await firstRefresh;
      await vi.advanceTimersByTimeAsync(150);
      await settleRefresh();

      // The drained wave carries only the late arrival, so it must extend the panel rather than
      // reseed it: a fresh panel drops every address the first wave finished and the denominator
      // falls mid-sync with nothing signalling that a second wave began.
      const [initial, drained] = mockTxQueryStatusStore.initializeQueryStatus.mock.calls;
      expect(initial).toEqual([
        [
          ...mockEvmAccounts.map(account => ({ ...account, subtype: 'evm' })),
          ...mockBitcoinAccounts.map(account => ({ ...account, subtype: 'bitcoin' })),
        ],
        { extend: false },
      ]);
      expect(drained).toEqual([[{ ...addedMidRefresh, subtype: 'evm' }], { extend: true }]);

      // One reset for the sync as a whole, not one per wave.
      expect(mockTxQueryStatusStore.resetQueryStatus).toHaveBeenCalledTimes(1);

      vi.useRealTimers();
    });

    it('should reopen the decoding progress gate on the drained wave', async () => {
      vi.useFakeTimers();

      const addedMidRefresh: ChainAddress = { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', chain: 'eth' };

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([...mockEvmAccounts, ...mockBitcoinAccounts, addedMidRefresh]);

      await refreshTransactions({ payload: { accounts: [addedMidRefresh] } });
      await firstRefresh;
      await vi.advanceTimersByTimeAsync(150);
      await settleRefresh();

      // `decodingSyncing` is the only gate on both decode-progress writers, and the first wave's
      // `finally` turns it off. Without re-arming it the drained wave decodes invisibly: the panel
      // keeps the first wave's finished rows and reads complete while work is still running.
      expect(mockDecodingStatusStore.resumeDecodingSyncProgress).toHaveBeenCalledTimes(1);
      expect(mockDecodingStatusStore.resetDecodingSyncProgress).toHaveBeenCalledTimes(1);

      vi.useRealTimers();
    });

    it('should not queue accounts the running refresh already covers', async () => {
      vi.useFakeTimers();

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      const firstRefresh = refreshTransactions();

      await refreshTransactions({
        payload: { accounts: [mockEvmAccounts[0]] },
      });

      await firstRefresh;
      await vi.advanceTimersByTimeAsync(150);
      await settleRefresh();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledTimes(1);

      vi.useRealTimers();
    });
  });

  describe('chain filtering', () => {
    it('should filter accounts by specified chains', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        chains: ['eth'],
      });

      expect(mockHistoryTransactionAccounts.getAllAccounts).toHaveBeenCalledWith(['eth']);
    });
  });

  describe('disableEvmEvents parameter', () => {
    it('should execute only ETH_WITHDRAWALS and BLOCK_PRODUCTIONS queries when disableEvmEvents is true', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        disableEvmEvents: true,
        payload: {
          accounts: mockEvmAccounts,
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
        HISTORY_SYNC_ID,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
        HISTORY_SYNC_ID,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(2);
    });

    it('should execute custom queries when disableEvmEvents is false', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        disableEvmEvents: false,
        payload: {
          accounts: mockEvmAccounts,
          queries: [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS],
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
        HISTORY_SYNC_ID,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe('online queries', () => {
    it('should execute ETH_WITHDRAWALS and BLOCK_PRODUCTIONS queries on full refresh', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
        HISTORY_SYNC_ID,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
        HISTORY_SYNC_ID,
      );
    });

    it('should execute custom queries when specified', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: {
          queries: [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS],
        },
      });

      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledWith(
        OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
        HISTORY_SYNC_ID,
      );
      expect(mockRefreshHandlers.queryOnlineEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe('error handling', () => {
    it('should settle the umbrella when an operation throws', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();
      await settleRefresh();

      // A throw is contained inside `run`, so nothing is left in flight to block the next refresh —
      // but it is still the account half failing, so no completion is recorded.
      expect(historySyncStatus().active).toBe(false);
      expect(historySyncStatus().everCompleted).toBe(false);
    });

    it('should not record a completion when every operation failed', async () => {
      failEverything();
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();
      await settleRefresh();

      expect(historySyncStatus().everCompleted).toBe(false);
      expect(historySyncStatus().active).toBe(false);
    });

    it('should not record a completion when the sync was cancelled', async () => {
      // Cancelling is not loading. If a stopped sync wrote the completion, `alreadyLoaded` would
      // suppress the next background refresh and the data the user interrupted would never arrive.
      mockTransactionSync.syncTransactionsByChains.mockResolvedValue([err(Cancelled({ message: 'stopped' }))]);
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();
      await settleRefresh();

      expect(historySyncStatus().everCompleted).toBe(false);
      expect(historySyncStatus().active).toBe(false);
    });

    it('should not let a successful online query mask a total chain failure', async () => {
      // The umbrella's freshness gates the *account* scope, so chains failing wholesale must fail
      // it whatever else succeeded — otherwise `alreadyLoaded` short-circuits the background re-sync.
      failEverything();
      mockRefreshHandlers.queryOnlineEvent.mockResolvedValue(ok(undefined));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();
      await settleRefresh();

      expect(historySyncStatus().everCompleted).toBe(false);
    });

    it('should still sync every account on a background refresh after an all-failed first sync', async () => {
      failEverything();
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      // Every account has now been *attempted*, so none is novel — which is why the failed first
      // load has to be recovered by scope, not by novelty.
      markAttempted();
      succeedEverything();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions();
      await settleRefresh();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining(mockEvmAccounts),
        expect.anything(),
        HISTORY_SYNC_ID,
      );
      expect(historySyncStatus().everCompleted).toBe(true);
    });

    it('should continue with other operations when one fails', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockUndecodedTransactionsStatus.fetchUndecodedTransactionsBreakdown).toHaveBeenCalled();
    });

    it('should still call finishRefresh and cleanup on error', async () => {
      mockUndecodedTransactionsStatus.fetchUndecodedTransactionsBreakdown.mockRejectedValueOnce(
        new Error('Fatal error'),
      );
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTxQueryStatusStore.stopSyncing).toHaveBeenCalled();
      expect(mockEventsQueryStatusStore.stopSyncing).toHaveBeenCalled();
      expect(mockDecodingStatusStore.stopDecodingSyncProgress).toHaveBeenCalled();
    });
  });

  describe('transaction chain type sync', () => {
    it('should sync EVM transactions', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ chain: 'eth' }),
          expect.objectContaining({ chain: 'optimism' }),
        ]),
        true, // shouldShowSyncProgress is true because isFirstLoad() returns true
        HISTORY_SYNC_ID,
      );
    });

    it('should sync Bitcoin transactions', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ chain: 'btc' }),
        ]),
        true, // shouldShowSyncProgress is true because isFirstLoad() returns true
        HISTORY_SYNC_ID,
      );
    });

    it('should not sync transactions for empty account types', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });
  });

  describe('query status management', () => {
    // Seeded from the same set that gets synced, subtype included.
    it('should initialize query status for every synced account, bitcoin included', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTxQueryStatusStore.initializeQueryStatus).toHaveBeenCalledWith(
        [
          ...mockEvmAccounts.map(account => ({ ...account, subtype: 'evm' })),
          ...mockBitcoinAccounts.map(account => ({ ...account, subtype: 'bitcoin' })),
        ],
        { extend: false },
      );
    });

    it('should reset query status when no accounts to refresh', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: [], exchanges: [] },
      });

      expect(mockTxQueryStatusStore.resetQueryStatus).toHaveBeenCalled();
    });
  });

  describe('userInitiated parameter', () => {
    it('should refresh already loaded history when user initiated', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions({ userInitiated: true });

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalled();
    });

    it('should skip an already loaded refresh when userInitiated is left to default', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions({ chains: [] });

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });
  });

  describe('scheduler state hooks', () => {
    it('should call onHistoryStarted when refresh starts with accounts', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryStarted).toHaveBeenCalledTimes(1);
    });

    it('should call onHistoryFinished when refresh completes', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryFinished).toHaveBeenCalledTimes(1);
    });

    it('should call onHistoryFinished even when errors occur', async () => {
      mockTransactionSync.syncTransactionsByChains.mockRejectedValue(new Error('Sync failed'));
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockOnHistoryFinished).toHaveBeenCalledTimes(1);
    });

    it('should not call onHistoryStarted when no accounts or exchanges to refresh', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue([]);
      set(mockExchangeData.syncingExchanges, []);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { accounts: [], exchanges: [] },
      });

      expect(mockOnHistoryStarted).not.toHaveBeenCalled();
    });

    it('should call onHistoryStarted before sync operations', async () => {
      const callOrder: string[] = [];

      mockOnHistoryStarted.mockImplementation(() => {
        callOrder.push('onHistoryStarted');
      });
      mockTransactionSync.syncTransactionsByChains.mockImplementation(async (): SyncOutcomes => {
        callOrder.push('syncTransactionsByChains');
        return [ok(undefined)];
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(callOrder.indexOf('onHistoryStarted')).toBeLessThan(callOrder.indexOf('syncTransactionsByChains'));
    });

    it('should stop decoding sync progress only after the sync work has finished', async () => {
      const callOrder: string[] = [];

      // The umbrella awaits its children, so an early `stopDecodingSyncProgress()` cannot drop the
      // WS progress updates decoding pushes.
      mockTransactionSync.syncTransactionsByChains.mockImplementation(async (): SyncOutcomes => {
        callOrder.push('syncTransactionsByChains');
        return [ok(undefined)];
      });
      mockDecodingStatusStore.stopDecodingSyncProgress.mockImplementation(() => {
        callOrder.push('stopDecodingSyncProgress');
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(callOrder.indexOf('syncTransactionsByChains')).toBeLessThan(callOrder.indexOf('stopDecodingSyncProgress'));
    });

    it('should call onHistoryFinished after all operations complete', async () => {
      const callOrder: string[] = [];

      mockTransactionSync.syncTransactionsByChains.mockImplementation(async (): SyncOutcomes => {
        callOrder.push('syncTransactionsByChains');
        return [ok(undefined)];
      });
      mockOnHistoryFinished.mockImplementation(() => {
        callOrder.push('onHistoryFinished');
      });

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(callOrder.indexOf('syncTransactionsByChains')).toBeLessThan(callOrder.indexOf('onHistoryFinished'));
    });
  });

  describe('exchange filtering', () => {
    it('should filter out exchanges not in syncingExchanges', async () => {
      const unknownExchange: Exchange = { location: 'unknown_exchange', name: 'Unknown' };
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions({
        payload: { exchanges: [mockExchanges[0], unknownExchange] },
      });

      expect(mockRefreshHandlers.queryAllExchangeEvents).toHaveBeenCalledWith([mockExchanges[0]], HISTORY_SYNC_ID);
    });
  });

  describe('pending drain', () => {
    it('should not schedule a drain when nothing is left unattempted', async () => {
      vi.useFakeTimers();

      // State the precondition rather than relying on this refresh to establish it: every account
      // and exchange has been attempted, so the ledger has nothing novel left to report.
      markAttempted();

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions({ userInitiated: true });
      await settleRefresh();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await vi.advanceTimersByTimeAsync(150);

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('sync progress', () => {
    it('should not initialize query status when not first load and no novel items', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTxQueryStatusStore.initializeQueryStatus.mockClear();
      mockDecodingStatusStore.resetUndecodedTransactionsStatus.mockClear();

      await refreshTransactions({ userInitiated: true });

      expect(mockTxQueryStatusStore.initializeQueryStatus).not.toHaveBeenCalled();
      expect(mockDecodingStatusStore.resetUndecodedTransactionsStatus).not.toHaveBeenCalled();
    });
  });

  describe('full refresh with no new accounts', () => {
    it('should not refresh accounts when history has loaded and none are new', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      // A real completed load, which is what makes "none are novel" mean "we already have it".
      await refreshTransactions();
      await settleRefresh();

      markAttempted();
      mockTransactionSync.syncTransactionsByChains.mockClear();

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
    });

    it('should refresh every account when nothing is novel but history never loaded', async () => {
      // The distinguishing case: attempted but never completed is what an all-failed or cancelled
      // first sync leaves behind, and novelty alone reads it as "nothing to do".
      markAttempted();
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockTransactionSync.syncTransactionsByChains).toHaveBeenCalledWith(
        expect.arrayContaining(mockEvmAccounts),
        expect.anything(),
        HISTORY_SYNC_ID,
      );
    });
  });

  describe('undecoded transactions', () => {
    it('should queue fetchUndecodedTransactionsBreakdown after operations complete', async () => {
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockUndecodedTransactionsStatus.fetchUndecodedTransactionsBreakdown).toHaveBeenCalled();
    });

    it('should read the breakdown twice for decodable accounts, not three times', async () => {
      // Once before the operations and once after them, never a third.
      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      expect(mockUndecodedTransactionsStatus.fetchUndecodedTransactionsBreakdown).toHaveBeenCalledTimes(2);
    });

    it('should still read the breakdown when no account is decodable', async () => {
      mockHistoryTransactionAccounts.getAllAccounts.mockReturnValue(mockBitcoinAccounts);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;

      await refreshTransactions();

      // The pre-operation read is a full-refresh concern, the post-operation one is unconditional.
      expect(mockUndecodedTransactionsStatus.fetchUndecodedTransactionsBreakdown).toHaveBeenCalledTimes(2);
    });
  });

  describe('disabled chain queries', () => {
    it('should not start a refresh when every requested account is disabled', async () => {
      mockDisabledChains.filterAccounts.mockReturnValue([]);
      set(mockExchangeData.syncingExchanges, []);

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions({ payload: { accounts: mockEvmAccounts } });

      expect(mockTxQueryStatusStore.initializeQueryStatus).not.toHaveBeenCalled();
      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();
      expect(mockOnHistoryStarted).not.toHaveBeenCalled();
    });

    it('should also filter explicit caller-supplied accounts', async () => {
      mockDisabledChains.filterAccounts.mockImplementation(
        (accounts: ChainAddress[]) => accounts.filter(account => account.chain !== 'eth'),
      );

      const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
      await refreshTransactions({
        payload: { accounts: mockEvmAccounts },
        userInitiated: true,
      });

      const syncArgs = mockTransactionSync.syncTransactionsByChains.mock.calls[0]?.[0] ?? [];
      expect(syncArgs).toEqual([mockEvmAccounts[1]]);
    });
  });

  describe('scope cleanup', () => {
    it('should clear pending timeout when scope is disposed', async () => {
      vi.useFakeTimers();

      const scope = effectScope();
      let refreshFn: ((params?: RefreshTransactionsParams) => Promise<void>) | undefined;

      scope.run(() => {
        const { refreshTransactions } = scope.run(() => useRefreshTransactions())!;
        refreshFn = refreshTransactions;
      });

      const firstRefresh = refreshFn!();
      await refreshFn!({ payload: { accounts: [mockEvmAccounts[0]] } });
      await firstRefresh;

      scope.stop();

      vi.clearAllMocks();
      await vi.advanceTimersByTimeAsync(150);

      expect(mockTransactionSync.syncTransactionsByChains).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });
});
