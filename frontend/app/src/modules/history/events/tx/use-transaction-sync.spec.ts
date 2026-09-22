import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import type { NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, Cancelled, isCancellation, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import { ActivityKind, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';
import { useTransactionSync } from './use-transaction-sync';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  decodeTransactionsTask: vi.fn(),
  statusOf: vi.fn(),
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
    statusOf: mocks.statusOf,
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: vi.fn((chain: string) => chain) })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>()),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => ({ decodeTransactionsTask: mocks.decodeTransactionsTask })),
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
    mocks.statusOf.mockReturnValue({ lastOutcome: undefined });
  });

  describe('syncTransactionTask', () => {
    it('should submit a native TX_SYNC activity keyed by chain and address', async () => {
      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account);

      expect(mocks.submitTask).toHaveBeenCalledOnce();
      expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
        id: makeActivityId(ActivityKind.TX_SYNC, 'ethereum', '0xABC'),
        kind: ActivityKind.TX_SYNC,
        rerunnable: true,
      });
    });

    it('should notify on an actionable failure', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account);

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });

    it.each([
      ['a cancel from the backend', BackendCancelled({ message: 'backend cancelled' })],
      ['a cancel from the user', Cancelled({ message: 'cancelled' })],
      ['a task skipped for a missing api key', Skipped({ message: 'no api key' })],
    ])('should not notify on %s, which is nothing to act on', async (_case, error) => {
      mocks.submitTask.mockResolvedValue(err(error));

      const { syncTransactionTask } = useTransactionSync();
      await syncTransactionTask(account);

      expect(mockNotifyError).not.toHaveBeenCalled();
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

    /** The decode's skip check, as the chain declared it. */
    async function decodeSkipWhen(): Promise<() => boolean> {
      const { syncAndReDecodeEvents } = useTransactionSync();
      await syncAndReDecodeEvents('eth', { accounts, type: TransactionChainType.EVM });

      const placement = mocks.decodeTransactionsTask.mock.calls[0][2];
      assert(placement?.skipWhen);
      return placement.skipWhen;
    }

    it('should skip the decode when every account\'s sync ended cancelled', async () => {
      mocks.statusOf.mockReturnValue({ lastOutcome: ActivityStatus.CANCELLED });

      expect((await decodeSkipWhen())()).toBe(true);
    });

    it('should still run the decode when any account\'s sync finished', async () => {
      mocks.statusOf.mockImplementation((_kind: ActivityKind, _chain: string, address: string) => ({
        lastOutcome: address === '0xAAA' ? ActivityStatus.CANCELLED : ActivityStatus.COMPLETE,
      }));

      expect((await decodeSkipWhen())()).toBe(false);
    });

    it('should ask about each account by the id its sync runs under before skipping the decode', async () => {
      mocks.statusOf.mockReturnValue({ lastOutcome: ActivityStatus.CANCELLED });
      (await decodeSkipWhen())();

      expect(mocks.statusOf).toHaveBeenCalledWith(ActivityKind.TX_SYNC, 'eth', '0xAAA');
      expect(mocks.statusOf).toHaveBeenCalledWith(ActivityKind.TX_SYNC, 'eth', '0xBBB');
    });
  });
});
