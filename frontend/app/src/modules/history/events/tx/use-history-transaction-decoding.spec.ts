import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { createMock } from '@test/utils/create-mock';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useHistoryTransactionDecoding } from './use-history-transaction-decoding';

const mockNotifyError = vi.fn();

interface UndecodedStatus {
  chain: string;
  processed: number;
  total: number;
}

const mocks = vi.hoisted(() => ({
  markDecodingCancelled: vi.fn(),
  runTaskResult: vi.fn(),
  submitTask: vi.fn(),
  undecodedStatus: new Array<{ chain: string; processed: number; total: number }>(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: mocks.runTaskResult,
    statusOf: vi.fn(() => ({ active: false, everCompleted: false, pending: false, running: false })),
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
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>()),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    getUndecodedTransactionStatus: vi.fn(() => mocks.undecodedStatus),
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
    isBtcChains: vi.fn((chain: string) => ['btc', 'bch'].includes(chain)),
    isEvmLikeChains: vi.fn(() => false),
    isSolanaChains: vi.fn(() => false),
  })),
}));

describe('useHistoryTransactionDecoding', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.undecodedStatus = [];
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  describe('checkMissingEventsAndRedecode', () => {
    /**
     * Bitcoin decodes through its own backend path, never the EVM decode endpoint. It only reaches
     * this store once bitcoin reports decoding progress over the websocket, so the sweep's
     * "everything that is not evmlike is EVM" split silently starts claiming it.
     */
    it('should not sweep a bitcoin chain into the EVM decode', async () => {
      const seeded: UndecodedStatus[] = [
        { chain: 'eth', processed: 0, total: 5 },
        { chain: 'btc', processed: 0, total: 3 },
      ];
      mocks.undecodedStatus = seeded;

      const { checkMissingEventsAndRedecode } = useHistoryTransactionDecoding();
      await checkMissingEventsAndRedecode();

      const decoded = mocks.submitTask.mock.calls
        .filter(call => call[0].kind === ActivityKind.TX_DECODING)
        .map(call => call[0].id);

      expect(decoded).toContain(decodeActivityId('eth'));
      expect(decoded).not.toContain(decodeActivityId('btc'));
    });
  });

  describe('redecodeTransactions', () => {
    it('should complete the flow even when a chain fails', async () => {
      mocks.submitTask.mockImplementation(async (spec: {
        kind: string;
        run: (ctx: { report: () => void; runTask: unknown }) => Promise<unknown>;
      }) => {
        if (spec.kind === ActivityKind.TX_DECODING)
          return err(TaskFailed({ message: 'boom' }));

        return spec.run({ report: (): void => {}, runTask: mocks.runTaskResult });
      });

      const { redecodeTransactions } = useHistoryTransactionDecoding();

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
        id: decodeActivityId('ethereum'),
        kind: ActivityKind.TX_DECODING,
        rerunnable: true,
      });
    });

    /**
     * A refresh declares its per-chain decode up front with `deps` on every account sync, so it
     * sits PENDING with `ignoreCache: false` for the whole sync window. Keyed by chain alone,
     * "Redecode all transactions" pressed during that window was handed the pending run's
     * promise: the forced decode never reached the backend and the umbrella settled COMPLETE.
     */
    it('should not share an identity between a cache decode and a forced one', async () => {
      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum', false);
      await decodeTransactionsTask('ethereum', true);

      const [cached, forced] = mocks.submitTask.mock.calls.map(call => call[0].id);
      expect(cached).not.toBe(forced);
    });

    it.each([
      ['complete without a backend call when there is nothing to decode', true, 0],
      ['reach the backend when there is something to decode', false, 1],
    ])('should %s', async (_label: string, skip: boolean, calls: number) => {
      const runTask = vi.fn().mockResolvedValue(ok(true));
      mocks.submitTask.mockImplementation(async (spec: {
        run: (ctx: { report: () => void; runTask: unknown }) => Promise<unknown>;
      }) => spec.run({ report: (): void => {}, runTask }));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum', false, { skipWhen: () => skip });

      expect(runTask).toHaveBeenCalledTimes(calls);
      expect(mockNotifyError).not.toHaveBeenCalled();
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
