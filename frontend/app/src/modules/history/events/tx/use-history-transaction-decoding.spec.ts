import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useHistoryTransactionDecoding } from './use-history-transaction-decoding';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  markDecodingCancelled: vi.fn(),
  runTaskResult: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: mocks.runTaskResult,
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: vi.fn(() => ({
    runTask: vi.fn(),
  })),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({ isTaskRunning: vi.fn(() => false) })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => ({
    decodeTransactions: vi.fn(),
    getUndecodedTransactionsBreakdown: vi.fn(),
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    getUndecodedTransactionStatus: vi.fn(() => []),
    markDecodingCancelled: mocks.markDecodingCancelled,
    resetUndecodedTransactionsStatus: vi.fn(),
    updateUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    decodableTxChainsInfo: ref<{ id: string }[]>([]),
    getChain: vi.fn((chain: string) => chain),
    getChainName: vi.fn((chain: string) => chain),
    isEvmLikeChains: vi.fn(() => false),
    isSolanaChains: vi.fn(() => false),
  })),
}));

describe('useHistoryTransactionDecoding', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  describe('redecodeTransactions', () => {
    it('should complete the flow even when a chain fails', async () => {
      // The umbrella runs for real; every child decode fails.
      mocks.submitTask.mockImplementation(async (spec: {
        kind: string;
        run: (ctx: { report: () => void; runTask: unknown }) => Promise<unknown>;
      }) => {
        if (spec.kind === ActivityKind.TX_DECODING)
          return err(TaskFailed({ message: 'boom' }));

        return spec.run({ report: (): void => {}, runTask: mocks.runTaskResult });
      });

      const { redecodeTransactions } = useHistoryTransactionDecoding();

      // A failure marks the child, never the parent: to an observer the flow ran to completion, and
      // the chain that failed keeps its stale freshness so a later run retries just that one.
      await expect(redecodeTransactions(['ethereum', 'optimism'])).resolves.toBeUndefined();
      expect(mockNotifyError).toHaveBeenCalled();
    });
  });

  describe('decodeTransactionsTask', () => {
    it('should submit a native TX_DECODING activity keyed by chain', async () => {
      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum');

      expect(mocks.submitTask).toHaveBeenCalledOnce();
      expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
        id: makeActivityId(ActivityKind.TX_DECODING, 'ethereum'),
        kind: ActivityKind.TX_DECODING,
        rerunnable: true,
      });
    });

    it('should mark decoding cancelled on a cancellation', async () => {
      mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum');

      expect(mocks.markDecodingCancelled).toHaveBeenCalledWith('ethereum');
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum');

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mocks.markDecodingCancelled).not.toHaveBeenCalled();
    });
  });
});
