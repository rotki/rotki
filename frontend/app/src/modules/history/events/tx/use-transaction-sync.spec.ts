import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { useTransactionSync } from './use-transaction-sync';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  markAddressCancelled: vi.fn(),
  markAddressFailed: vi.fn(),
  removeQueryStatus: vi.fn(),
  runTask: vi.fn(),
  setEvmlikeStatus: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: vi.fn(() => ({ runTask: mocks.runTask })),
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

  const failure = (fields: {
    backendCancelled?: boolean;
    cancelled?: boolean;
    skipped?: boolean;
  }): object => ({
    backendCancelled: false,
    cancelled: false,
    message: 'boom',
    skipped: false,
    success: false,
    ...fields,
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.runTask.mockResolvedValue({ result: true, success: true });
  });

  describe('syncTransactionTask', () => {
    it('should remove the query status when the backend cancels', async () => {
      mocks.runTask.mockResolvedValue(failure({ backendCancelled: true, cancelled: true }));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.removeQueryStatus).toHaveBeenCalledWith(account);
      expect(mocks.markAddressFailed).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should mark the address cancelled on a user cancel', async () => {
      mocks.runTask.mockResolvedValue(failure({ cancelled: true }));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mocks.markAddressCancelled).toHaveBeenCalledWith(account);
      expect(mocks.markAddressFailed).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should mark the address failed and notify when the query fails', async () => {
      mocks.runTask.mockResolvedValue(failure({}));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account, TransactionChainType.EVM);

      expect(mockNotifyError).toHaveBeenCalledOnce();
      // Nothing else moves this entry off "querying": evmlike chains send no websocket messages at
      // all, and evm chains report the query as finished even when it raised.
      // The chain type rides along so the entry can be synthesized when the failure arrived before
      // any status message did.
      expect(mocks.markAddressFailed).toHaveBeenCalledWith(account, TransactionChainType.EVM);
      // Marked, NOT removed: the sync panel derives its chain list from these entries, so removing
      // it took the whole chain out of the panel and out of its own denominator.
      expect(mocks.removeQueryStatus).not.toHaveBeenCalled();
      expect(mocks.markAddressCancelled).not.toHaveBeenCalled();
    });

    it('should leave a skipped task alone', async () => {
      // A skipped task never ran, so it has not failed and must not be reported as such.
      mocks.runTask.mockResolvedValue(failure({ skipped: true }));

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
});
