import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import type { NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, Cancelled, isCancellation, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTransactionSync } from './use-transaction-sync';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  markAddressCancelled: vi.fn(),
  markAddressFailed: vi.fn(),
  removeQueryStatus: vi.fn(),
  setEvmlikeStatus: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: vi.fn(),
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/history/use-tx-query-status-store', () => ({
  useTxQueryStatusStore: vi.fn(() => ({
    isAddressCancelled: vi.fn(() => false),
    markAddressCancelled: mocks.markAddressCancelled,
    markAddressFailed: mocks.markAddressFailed,
    removeQueryStatus: mocks.removeQueryStatus,
    setEvmlikeStatus: mocks.setEvmlikeStatus,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: vi.fn((chain: string) => chain) })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>()),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => ({ decodeTransactionsTask: vi.fn() })),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-accounts', () => ({
  useHistoryTransactionAccounts: vi.fn(() => ({ getTransactionTypeFromChain: vi.fn(() => TransactionChainType.EVM) })),
}));

describe('useTransactionSync', () => {
  const account: ChainAddress = { address: '0xABC', chain: 'ethereum' };

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  describe('syncTransactionTask', () => {
    it('should submit a native TX_SYNC activity keyed by chain and address', async () => {
      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.submitTask).toHaveBeenCalledOnce();
      expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
        id: makeActivityId(ActivityKind.TX_SYNC, 'ethereum', '0xABC'),
        kind: ActivityKind.TX_SYNC,
        rerunnable: true,
      });
    });

    it('should remove the query status when the backend cancels', async () => {
      mocks.submitTask.mockResolvedValue(err(BackendCancelled({ message: 'backend cancelled' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.removeQueryStatus).toHaveBeenCalledWith(account);
      expect(mocks.markAddressCancelled).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should mark the address cancelled on a user cancel', async () => {
      mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.markAddressCancelled).toHaveBeenCalledWith(account);
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure and mark the address failed', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mockNotifyError).toHaveBeenCalledOnce();
      // A failed query never sends the completion websocket message, so nothing else would ever
      // move this entry off "querying".
      // The chain type rides along so a synthesized entry carries the right subtype; defaulting to
      // evm would wrongly describe an evmlike or bitcoin address.
      expect(mocks.markAddressFailed).toHaveBeenCalledWith(account, TransactionChainType.EVM);
      // Marked, NOT removed: the sync panel derives its chain list from these entries, so removing
      // it took the whole chain out of the panel and out of its own denominator.
      expect(mocks.removeQueryStatus).not.toHaveBeenCalled();
      expect(mocks.markAddressCancelled).not.toHaveBeenCalled();
    });

    it('should leave a skipped task alone', async () => {
      // A skipped task never ran, so it has not failed and must not be reported as such. A chain
      // with no API key reports Skipped, and a bare `else` on the error would have marked it failed.
      mocks.submitTask.mockResolvedValue(err(Skipped({ message: 'no api key' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.markAddressFailed).not.toHaveBeenCalled();
      expect(mocks.removeQueryStatus).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should bracket evmlike progress with started/finished', async () => {
      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVMLIKE);

      expect(mocks.setEvmlikeStatus).toHaveBeenNthCalledWith(1, account, 'started');
      expect(mocks.setEvmlikeStatus).toHaveBeenNthCalledWith(2, account, 'finished');
    });
  });

  describe('syncAndReDecodeEvents', () => {
    const chainId = makeActivityId(ActivityKind.TX_SYNC, 'eth');
    const accounts: ChainAddress[] = [
      { address: '0xAAA', chain: 'eth' },
      { address: '0xBBB', chain: 'eth' },
    ];

    /**
     * Runs the chain activity's own body instead of stubbing its outcome — the verdict it computes
     * from its children is the thing under test, and a `submitTask` that only resolves `ok` would
     * report every one of these tests as passing whatever the body did.
     */
    function runChainBody(...accountOutcomes: Result<void, TaskError>[]): void {
      let account = 0;
      mocks.submitTask.mockImplementation(async (spec: NativeActivitySpec) => {
        if (spec.id !== chainId)
          return accountOutcomes[account++] ?? ok(undefined);

        return spec.run({ cancelled: (): boolean => false, report: vi.fn(), runTask: vi.fn() });
      });
    }

    it('should complete when at least one account synced', async () => {
      runChainBody(err(TaskFailed({ message: 'boom' })), ok(undefined));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      expect(outcome.ok).toBe(true);
    });

    it('should fail when every account failed', async () => {
      // 🔴 The children never reject — each handles its own error and returns — so the chain used to
      // return `ok` unconditionally and report a whole failed chain as synced.
      runChainBody(err(TaskFailed({ message: 'boom' })), err(TaskFailed({ message: 'boom' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(outcome.error.message).toBe('boom');
    });

    it('should settle cancelled, not failed, when its accounts were cancelled', async () => {
      // The chain's verdict now folds its children's outcomes, so cancellation has to survive that
      // fold: reporting a user-stopped chain as FAILED would put an error row in the task centre for
      // something the user chose to stop.
      runChainBody(err(Cancelled({ message: 'stopped' })), err(BackendCancelled({ message: 'stopped' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(isCancellation(outcome.error)).toBe(true);
    });

    it('should report a real failure over a cancellation', async () => {
      // The other side of the same fold: a chain where one address genuinely failed and the rest were
      // cancelled is a failure worth surfacing. (A user cancelling the chain *itself* still reads
      // CANCELLED — `cancelRequested` overrides the run's outcome in the orchestrator.)
      runChainBody(err(TaskFailed({ message: 'boom' })), err(Cancelled({ message: 'stopped' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(isCancellation(outcome.error)).toBe(false);
    });

    it('should declare the chain activity as a container', async () => {
      runChainBody();
      const { syncAndReDecodeEvents } = useTransactionSync();

      await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      // It groups the per-account syncs, which carry the same kind and write their own ledger
      // entries; a completion recorded here would claim freshness for the chain on their behalf.
      expect(mocks.submitTask).toHaveBeenCalledWith(expect.objectContaining({ container: true, id: chainId }));
    });
  });

  /**
   * Against the real store rather than the mock above.
   *
   * A failing evmlike query calls `markAddressFailed` and then the unconditional `finished` tail,
   * and the defect was in what the second call did to the first one's result. Every assertion in
   * this file's other tests is on the mock recording that a call happened, which is true either
   * way, so none of them can see it. This one asserts the status the address is actually left in.
   */
  describe('evmlike failure against the real query-status store', () => {
    const evmlikeAccount: ChainAddress = { address: '0xABC', chain: 'zksync_lite' };

    beforeEach(() => {
      vi.resetModules();
      vi.doUnmock('@/modules/history/use-tx-query-status-store');
      setActivePinia(createPinia());
    });

    it('should leave a failed evmlike address failed, not complete', async () => {
      const { useTxQueryStatusStore } = await import('@/modules/history/use-tx-query-status-store');
      const { TransactionsQueryStatus } = await import('@/modules/core/messaging/types');
      const { useTransactionSync: useRealStoreSync } = await import('./use-transaction-sync');

      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const store = useTxQueryStatusStore();

      const { syncTransactionTask } = useRealStoreSync();
      await syncTransactionTask(evmlikeAccount, TransactionChainType.EVMLIKE);

      expect(get(store.queryStatus)['0xABCzksync_lite'].status).toBe(TransactionsQueryStatus.FAILED);
    });
  });
});
