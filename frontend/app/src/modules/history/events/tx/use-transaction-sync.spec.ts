import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
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
  useHistoryEventsApi: vi.fn(() => ({ fetchTransactionsTask: vi.fn() })),
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
      expect(mocks.markAddressFailed).toHaveBeenCalledWith(account);
      // Marked, NOT removed: the sync panel derives its chain list from these entries, so removing
      // it took the whole chain out of the panel and out of its own denominator.
      expect(mocks.removeQueryStatus).not.toHaveBeenCalled();
      expect(mocks.markAddressCancelled).not.toHaveBeenCalled();
    });

    it('should bracket evmlike progress with started/finished', async () => {
      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVMLIKE);

      expect(mocks.setEvmlikeStatus).toHaveBeenNthCalledWith(1, account, 'started');
      expect(mocks.setEvmlikeStatus).toHaveBeenNthCalledWith(2, account, 'finished');
    });
  });
});
