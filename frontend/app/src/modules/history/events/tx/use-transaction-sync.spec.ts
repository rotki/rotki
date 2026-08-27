import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import type { NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
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

    it('should notify on an actionable failure and mark the address failed with the chain type it was queried under', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mocks.markAddressFailed).toHaveBeenCalledWith(account, TransactionChainType.EVM);
      expect(mocks.removeQueryStatus).not.toHaveBeenCalled();
      expect(mocks.markAddressCancelled).not.toHaveBeenCalled();
    });

    it('should leave a task skipped for a missing api key alone, rather than reporting it as failed', async () => {
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

    let chainBodyRan: boolean;

    function runChainBody(...accountOutcomes: Result<void, TaskError>[]): void {
      let account = 0;
      mocks.submitTask.mockImplementation(async (spec: NativeActivitySpec) => {
        if (spec.id !== chainId)
          return accountOutcomes[account++] ?? ok(undefined);

        chainBodyRan = true;
        return spec.run({ cancelled: (): boolean => false, report: vi.fn(), runTask: vi.fn() });
      });
    }

    beforeEach(() => {
      chainBodyRan = false;
      runChainBody();
    });

    afterEach(() => {
      expect(chainBodyRan).toBe(true);
    });

    it('should complete when at least one account synced', async () => {
      runChainBody(err(TaskFailed({ message: 'boom' })), ok(undefined));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      expect(outcome.ok).toBe(true);
    });

    it('should fail when every account failed, even though no child rejects', async () => {
      runChainBody(err(TaskFailed({ message: 'boom' })), err(TaskFailed({ message: 'boom' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(outcome.error.message).toBe('boom');
    });

    it('should settle cancelled, not failed, when its accounts were cancelled', async () => {
      runChainBody(err(Cancelled({ message: 'stopped' })), err(BackendCancelled({ message: 'stopped' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(isCancellation(outcome.error)).toBe(true);
    });

    it('should report a real failure over a cancellation when one account failed and the rest were cancelled', async () => {
      runChainBody(err(TaskFailed({ message: 'boom' })), err(Cancelled({ message: 'stopped' })));
      const { syncAndReDecodeEvents } = useTransactionSync();

      const outcome = await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      assert(!outcome.ok);
      expect(isCancellation(outcome.error)).toBe(false);
    });

    it('should declare the chain activity as a container', async () => {
      const { syncAndReDecodeEvents } = useTransactionSync();

      await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      expect(mocks.submitTask).toHaveBeenCalledWith(expect.objectContaining({ container: true, id: chainId }));
    });
  });

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
