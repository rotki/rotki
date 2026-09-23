import type { ActivityContext, NativeActivitySpec, TaskOutcome } from '@/modules/task-center/use-native-task';
import { type Notification, Priority, Severity } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { isErr } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { ActivityKind, type ActivitySteps } from '@/modules/task-center/core/types';
import { type InternalTxConflict, InternalTxConflictActions } from './types';
import { type ResolutionCallbacks, useInternalTxConflictResolution } from './use-internal-tx-conflict-resolution';

interface DockState {
  /** what the dock's cancel reads back to the running activity */
  cancelled: boolean;
  outcomes: TaskOutcome<unknown>[];
  reported: ActivitySteps[];
  submitted: NativeActivitySpec<unknown>[];
}

const dock: DockState = { cancelled: false, outcomes: [], reported: [], submitted: [] };

const { spies } = vi.hoisted(() => ({
  spies: {
    cancelDecoding: vi.fn<() => Promise<void>>(),
    notify: vi.fn<(payload: Notification) => void>(),
    pullAndDecodeTransactionsRaw: vi.fn<(payload: unknown, parent?: string) => Promise<void>>(),
    removeKeys: vi.fn(),
  },
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({
    submitTask: async <T>(spec: NativeActivitySpec<T>): Promise<TaskOutcome<T>> => {
      dock.submitted.push(spec);
      const outcome = await spec.run(createMock<ActivityContext>({
        cancelled: () => dock.cancelled,
        report: (steps: ActivitySteps): void => {
          dock.reported.push({ ...steps });
        },
      }));
      dock.outcomes.push(outcome);
      return outcome;
    },
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChain: (location: string): string => {
      const map: Record<string, string> = { ethereum: 'eth', optimism: 'opt' };
      return map[location] ?? location;
    },
  }),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: (): object => ({
    cancelDecoding: spies.cancelDecoding,
  }),
}));

vi.mock('@/modules/history/events/tx/use-targeted-redecode', () => ({
  useTargetedRedecode: (): object => ({
    pullAndDecodeTransactionsRaw: spies.pullAndDecodeTransactionsRaw,
  }),
}));

vi.mock('./use-internal-tx-conflict-selection', () => ({
  useInternalTxConflictSelection: (): object => ({
    removeKeys: spies.removeKeys,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({
    notify: spies.notify,
    removeMatching: vi.fn(),
  }),
}));

function createMockConflict(overrides: Partial<InternalTxConflict> = {}): InternalTxConflict {
  return {
    action: InternalTxConflictActions.REPULL,
    chain: 'ethereum',
    groupIdentifier: null,
    lastError: null,
    lastRetryTs: null,
    redecodeReason: null,
    repullReason: 'all_zero_gas',
    timestamp: null,
    txHash: '0xabc',
    ...overrides,
  };
}

describe('use-internal-tx-conflict-resolution', () => {
  let composable: ReturnType<typeof useInternalTxConflictResolution>;
  let callbacks: ResolutionCallbacks;
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    spies.pullAndDecodeTransactionsRaw.mockReset();
    spies.cancelDecoding.mockReset();
    spies.removeKeys.mockReset();
    spies.notify.mockReset();
    dock.cancelled = false;
    dock.outcomes = [];
    dock.reported = [];
    dock.submitted = [];
    spies.pullAndDecodeTransactionsRaw.mockResolvedValue(undefined);
    spies.cancelDecoding.mockResolvedValue(undefined);
    scope = effectScope();
    scope.run(() => {
      composable = useInternalTxConflictResolution();
    });
    callbacks = { onComplete: vi.fn() };
  });

  afterEach(() => {
    scope.stop();
    vi.restoreAllMocks();
  });

  describe('resolveOne', () => {
    it('calls pullAndDecodeTransactionsRaw for repull action', async () => {
      const conflict = createMockConflict({ action: InternalTxConflictActions.REPULL, chain: 'ethereum' });
      await composable.resolveOne(conflict, callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledWith({
        chain: 'eth',
        txRefs: ['0xabc'],
      }, undefined);
      expect(spies.removeKeys).toHaveBeenCalledWith(['ethereum:0xabc']);
      expect(callbacks.onComplete).toHaveBeenCalled();
    });

    it('calls pullAndDecodeTransactionsRaw for fix_redecode action', async () => {
      const conflict = createMockConflict({
        action: InternalTxConflictActions.FIX_REDECODE,
        chain: 'ethereum',
        redecodeReason: 'duplicate_exact_rows',
        repullReason: null,
        txHash: '0xdef',
      });
      await composable.resolveOne(conflict, callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledWith({
        chain: 'eth',
        txRefs: ['0xdef'],
      }, undefined);
      expect(spies.removeKeys).toHaveBeenCalledWith(['ethereum:0xdef']);
      expect(callbacks.onComplete).toHaveBeenCalled();
    });

    it('handles errors without removing keys', async () => {
      spies.pullAndDecodeTransactionsRaw.mockRejectedValue(new Error('Network error'));
      const conflict = createMockConflict();
      await composable.resolveOne(conflict, callbacks);

      expect(callbacks.onComplete).toHaveBeenCalled();
      expect(spies.removeKeys).not.toHaveBeenCalled();
    });

    it('tracks resolving state per conflict', async () => {
      let resolveCall: (() => void) | undefined;
      spies.pullAndDecodeTransactionsRaw.mockImplementationOnce(
        async (): Promise<void> => new Promise<void>((resolve) => {
          resolveCall = resolve;
        }),
      );

      const conflict = createMockConflict();
      const promise = composable.resolveOne(conflict, callbacks);

      expect(composable.isResolving(conflict)).toBe(true);

      resolveCall?.();
      await promise;

      expect(composable.isResolving(conflict)).toBe(false);
    });
  });

  describe('resolveMany', () => {
    it('should run as one task dock activity that reports how many conflicts are done', async () => {
      await composable.resolveMany([createMockConflict(), createMockConflict({ txHash: '0xdef' })], callbacks);

      expect(dock.submitted).toHaveLength(1);
      expect(dock.submitted[0]).toMatchObject({ kind: ActivityKind.REPULLING, userStarted: true });
      expect(dock.reported).toEqual([{ current: 0, total: 2 }, { current: 1, total: 2 }, { current: 2, total: 2 }]);
    });

    it('should decode each conflict under the dock activity, so the dock lists it there', async () => {
      await composable.resolveMany([createMockConflict()], callbacks);

      const [activity] = dock.submitted;
      assert(activity);
      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledWith({ chain: 'eth', txRefs: ['0xabc'] }, activity.id);
    });

    it('should report the outcome once, below the popup threshold, and no progress along the way', async () => {
      await composable.resolveMany([createMockConflict(), createMockConflict({ txHash: '0xdef' })], callbacks);

      expect(spies.notify).toHaveBeenCalledOnce();
      expect(spies.notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'internal_tx_conflicts.notifications.completed::2',
        priority: Priority.NORMAL,
        severity: Severity.INFO,
      }));
    });

    it('should end the dock activity as failed when a conflict could not be resolved, not as done', async () => {
      spies.pullAndDecodeTransactionsRaw.mockRejectedValueOnce(new Error('fail'));

      await composable.resolveMany([createMockConflict({ txHash: '0x111' }), createMockConflict({ txHash: '0x222' })], callbacks);

      const [outcome] = dock.outcomes;
      assert(outcome && isErr(outcome));
      expect(outcome.error).toMatchObject({
        _tag: 'TaskFailed',
        message: 'internal_tx_conflicts.notifications.completed_with_errors::1, 1, 2',
      });
    });

    it('should stop between two conflicts when the task dock cancels, and report the run as cancelled', async () => {
      spies.pullAndDecodeTransactionsRaw.mockImplementationOnce(async (): Promise<void> => {
        dock.cancelled = true;
      });

      await composable.resolveMany([createMockConflict({ txHash: '0x111' }), createMockConflict({ txHash: '0x222' })], callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledOnce();
      expect(spies.notify).toHaveBeenCalledWith(expect.objectContaining({ severity: Severity.WARNING }));
    });

    it('processes each conflict individually', async () => {
      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'ethereum', txHash: '0x222' }),
        createMockConflict({ chain: 'optimism', txHash: '0x333' }),
      ];

      await composable.resolveMany(conflicts, callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledTimes(3);
      expect(spies.pullAndDecodeTransactionsRaw.mock.calls.map(([payload]) => payload)).toEqual([
        { chain: 'eth', txRefs: ['0x111'] },
        { chain: 'eth', txRefs: ['0x222'] },
        { chain: 'opt', txRefs: ['0x333'] },
      ]);
      expect(spies.removeKeys).toHaveBeenCalledTimes(3);
      expect(callbacks.onComplete).toHaveBeenCalledTimes(3);
    });

    it('handles mixed repull and redecode conflicts', async () => {
      const conflicts = [
        createMockConflict({ action: InternalTxConflictActions.REPULL, chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({
          action: InternalTxConflictActions.FIX_REDECODE,
          chain: 'ethereum',
          redecodeReason: 'duplicate_exact_rows',
          repullReason: null,
          txHash: '0x222',
        }),
      ];

      await composable.resolveMany(conflicts, callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledTimes(2);
    });

    it('increments failed counter on error and continues', async () => {
      spies.pullAndDecodeTransactionsRaw.mockRejectedValueOnce(new Error('fail'));
      spies.pullAndDecodeTransactionsRaw.mockResolvedValueOnce(undefined);

      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'optimism', txHash: '0x222' }),
      ];

      await composable.resolveMany(conflicts, callbacks);

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledTimes(2);
      expect(spies.removeKeys).toHaveBeenCalledWith(['optimism:0x222']);
      expect(callbacks.onComplete).toHaveBeenCalledTimes(2);
    });

    it('stops processing when cancel is requested', async () => {
      let resolveFirst: (() => void) | undefined;
      spies.pullAndDecodeTransactionsRaw.mockImplementationOnce(
        async (): Promise<void> => new Promise<void>((resolve) => {
          resolveFirst = resolve;
        }),
      );
      spies.pullAndDecodeTransactionsRaw.mockResolvedValueOnce(undefined);

      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'optimism', txHash: '0x222' }),
      ];

      const promise = composable.resolveMany(conflicts, callbacks);
      composable.cancelResolution();
      resolveFirst?.();
      await promise;

      expect(spies.pullAndDecodeTransactionsRaw).toHaveBeenCalledTimes(1);
    });
  });
});
