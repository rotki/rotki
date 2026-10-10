import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { redecodeFlow } from '@/modules/history/events/tx/redecode.flow';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useHistoryTransactionDecoding } from './use-history-transaction-decoding';

const mockNotifyError = vi.fn();

interface UndecodedStatus {
  chain: string;
  processed: number;
  total: number;
}

const mocks = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    decodeTransactions: vi.fn<ReturnType<typeof useHistoryEventsApi>['decodeTransactions']>(),
    runTaskResult: vi.fn(),
    submitTask: vi.fn(),
    txChains: ref<{ id: string }[]>([]),
    undecodedStatus: new Array<{ chain: string; processed: number; total: number }>(),
  };
});

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
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>({
    decodeTransactions: mocks.decodeTransactions,
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    getUndecodedTransactionStatus: vi.fn(() => mocks.undecodedStatus),
    resetUndecodedTransactionsStatus: vi.fn(),
    updateUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    allTxChainsInfo: mocks.txChains,
    getChain: vi.fn((chain: string) => chain),
    getChainName: vi.fn((chain: string) => chain),
  })),
}));

/** The ids of the chain decodes submitted so far, in submission order. */
function decodedIds(): string[] {
  return mocks.submitTask.mock.calls
    .filter(call => call[0].kind === ActivityKind.TX_DECODING)
    .map(call => call[0].id);
}

describe('useHistoryTransactionDecoding', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.undecodedStatus = [];
    set(mocks.txChains, []);
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  describe('checkMissingEventsAndRedecode', () => {
    it('should decode the pending transactions of every chain reporting some, bitcoin chains included, exactly once', async () => {
      const seeded: UndecodedStatus[] = [
        { chain: 'eth', processed: 0, total: 5 },
        { chain: 'btc', processed: 0, total: 3 },
        { chain: 'bch', processed: 1, total: 2 },
        { chain: 'solana', processed: 4, total: 4 },
      ];
      mocks.undecodedStatus = seeded;

      const { checkMissingEventsAndRedecode } = useHistoryTransactionDecoding();
      await checkMissingEventsAndRedecode();

      expect(decodedIds()).toStrictEqual([decodeActivityId('eth'), decodeActivityId('btc'), decodeActivityId('bch')]);
    });
  });

  describe('redecodeTransactions', () => {
    it('should complete the flow even when a chain fails, leaving that chain to its dock row', async () => {
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
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should force a decode of every chain with transactions, bitcoin chains included, when asked to redecode all', async () => {
      set(mocks.txChains, [{ id: 'eth' }, { id: 'btc' }, { id: 'bch' }]);

      await useHistoryTransactionDecoding().redecodeTransactions();

      expect(decodedIds()).toStrictEqual(['eth', 'btc', 'bch'].map(chain => decodeActivityId(chain, true)));
      expect(mocks.submitTask.mock.calls.find(call => call[0].kind === ActivityKind.REDECODE)?.[0]).toMatchObject({
        id: redecodeFlow.id(),
        subtitle: undefined,
      });
    });

    it('should keep a bitcoin-only request apart from the full run', async () => {
      set(mocks.txChains, [{ id: 'eth' }, { id: 'btc' }, { id: 'bch' }]);

      await useHistoryTransactionDecoding().redecodeTransactions(['btc', 'bch']);

      expect(decodedIds()).toStrictEqual([decodeActivityId('btc', true), decodeActivityId('bch', true)]);
      expect(mocks.submitTask.mock.calls.find(call => call[0].kind === ActivityKind.REDECODE)?.[0].id)
        .toBe(redecodeFlow.id(['btc', 'bch']));
    });

    it('should complete a redecode of everything when only the bitcoin decode failed', async () => {
      set(mocks.txChains, [{ id: 'eth' }, { id: 'btc' }]);
      let flow: Promise<Result<void, TaskError>> | undefined;
      mocks.submitTask.mockImplementation(async (spec: { id: string; kind: string; run: () => Promise<Result<void, TaskError>> }) => {
        if (spec.kind === ActivityKind.REDECODE) {
          flow = spec.run();
          return flow;
        }
        return spec.id === decodeActivityId('btc', true) ? err(TaskFailed({ message: 'boom' })) : ok(undefined);
      });

      await useHistoryTransactionDecoding().redecodeTransactions();

      assert(flow);
      expect((await flow).ok).toBe(true);
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    /** Runs the flow with each chain's decode answering as `outcomeOf` says, and returns the flow's own outcome. */
    async function flowOutcome(outcomeOf: (chain: string) => Result<void, TaskError>): Promise<Result<void, TaskError>> {
      let flow: Promise<Result<void, TaskError>> | undefined;
      mocks.submitTask.mockImplementation(async (spec: { id: string; kind: string; run: () => Promise<Result<void, TaskError>> }) => {
        if (spec.kind === ActivityKind.REDECODE) {
          flow = spec.run();
          return flow;
        }
        return outcomeOf(spec.id);
      });

      await useHistoryTransactionDecoding().redecodeTransactions(['ethereum', 'optimism']);
      assert(flow);
      return flow;
    }

    it('should fail the flow when every chain failed, rather than report the redecode done', async () => {
      const outcome = await flowOutcome(() => err(TaskFailed({ message: 'boom' })));

      assert(!outcome.ok);
      expect(outcome.error.message).toBe('boom');
    });

    it('should complete the flow when at least one chain decoded', async () => {
      const outcome = await flowOutcome(id => (id === decodeActivityId('ethereum', true) ? ok(undefined) : err(TaskFailed({ message: 'boom' }))));

      expect(outcome.ok).toBe(true);
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

    it('should send a forced bitcoin decode to the backend as that chain with the cache ignored', async () => {
      mocks.submitTask.mockImplementation(async (spec: {
        run: (ctx: { report: () => void; runTask: (task: () => Promise<unknown>) => Promise<Result<boolean, TaskError>> }) => Promise<unknown>;
      }) => spec.run({
        report: (): void => {},
        runTask: async (task) => {
          await task();
          return ok(true);
        },
      }));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('btc', true);

      expect(mocks.decodeTransactions).toHaveBeenCalledExactlyOnceWith('btc', true);
    });

    it('should not notify when the user cancelled the decode', async () => {
      mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum');

      expect(mocks.submitTask).toHaveBeenCalledOnce();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should leave an actionable failure to its dock row', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { decodeTransactionsTask } = useHistoryTransactionDecoding();
      await decodeTransactionsTask('ethereum');

      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });
});
