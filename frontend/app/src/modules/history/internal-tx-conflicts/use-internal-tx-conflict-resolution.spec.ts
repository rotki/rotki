import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { type InternalTxConflict, InternalTxConflictActions } from './types';
import { type ResolutionCallbacks, useInternalTxConflictResolution } from './use-internal-tx-conflict-resolution';

const { spies } = vi.hoisted(() => ({
  spies: {
    cancelTaskByTaskType: vi.fn<() => Promise<void>>(),
    pullAndRedecodeTransactions: vi.fn<() => Promise<void>>(),
    removeKeys: vi.fn(),
  },
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: (): object => ({
    getChain: (location: string): string => {
      const map: Record<string, string> = { ethereum: 'eth', optimism: 'opt' };
      return map[location] ?? location;
    },
  }),
}));

vi.mock('@/composables/history/events/tx/decoding', () => ({
  useHistoryTransactionDecoding: (): object => ({
    pullAndRedecodeTransactions: spies.pullAndRedecodeTransactions,
  }),
}));

vi.mock('./use-internal-tx-conflict-selection', () => ({
  useInternalTxConflictSelection: (): object => ({
    removeKeys: spies.removeKeys,
  }),
}));

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: (): object => ({
    notify: vi.fn(),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: (): object => ({
    cancelTaskByTaskType: spies.cancelTaskByTaskType,
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
    vi.clearAllMocks();
    spies.pullAndRedecodeTransactions.mockResolvedValue(undefined);
    spies.cancelTaskByTaskType.mockResolvedValue(undefined);
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
    it('calls pullAndRedecodeTransactions for repull action', async () => {
      const conflict = createMockConflict({ action: InternalTxConflictActions.REPULL, chain: 'ethereum' });
      await composable.resolveOne(conflict, callbacks);

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledWith({
        transactions: [{ location: 'eth', txRef: '0xabc' }],
      });
      expect(spies.removeKeys).toHaveBeenCalledWith(['ethereum:0xabc']);
      expect(callbacks.onComplete).toHaveBeenCalled();
    });

    it('calls pullAndRedecodeTransactions for fix_redecode action', async () => {
      const conflict = createMockConflict({
        action: InternalTxConflictActions.FIX_REDECODE,
        chain: 'ethereum',
        redecodeReason: 'duplicate_exact_rows',
        repullReason: null,
        txHash: '0xdef',
      });
      await composable.resolveOne(conflict, callbacks);

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledWith({
        transactions: [{ location: 'eth', txRef: '0xdef' }],
      });
      expect(spies.removeKeys).toHaveBeenCalledWith(['ethereum:0xdef']);
      expect(callbacks.onComplete).toHaveBeenCalled();
    });

    it('handles errors without removing keys', async () => {
      spies.pullAndRedecodeTransactions.mockRejectedValue(new Error('Network error'));
      const conflict = createMockConflict();
      await composable.resolveOne(conflict, callbacks);

      expect(callbacks.onComplete).toHaveBeenCalled();
      expect(spies.removeKeys).not.toHaveBeenCalled();
    });

    it('tracks resolving state per conflict', async () => {
      let resolveCall: (() => void) | undefined;
      spies.pullAndRedecodeTransactions.mockImplementationOnce(
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
    it('processes each conflict individually', async () => {
      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'ethereum', txHash: '0x222' }),
        createMockConflict({ chain: 'optimism', txHash: '0x333' }),
      ];

      await composable.resolveMany(conflicts, callbacks);

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledTimes(3);
      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledWith({
        transactions: [{ location: 'eth', txRef: '0x111' }],
      });
      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledWith({
        transactions: [{ location: 'eth', txRef: '0x222' }],
      });
      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledWith({
        transactions: [{ location: 'opt', txRef: '0x333' }],
      });
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

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledTimes(2);
    });

    it('increments failed counter on error and continues', async () => {
      spies.pullAndRedecodeTransactions.mockRejectedValueOnce(new Error('fail'));
      spies.pullAndRedecodeTransactions.mockResolvedValueOnce(undefined);

      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'optimism', txHash: '0x222' }),
      ];

      await composable.resolveMany(conflicts, callbacks);

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledTimes(2);
      expect(spies.removeKeys).toHaveBeenCalledWith(['optimism:0x222']);
      expect(callbacks.onComplete).toHaveBeenCalledTimes(2);
    });

    it('stops processing when cancel is requested', async () => {
      let resolveFirst: (() => void) | undefined;
      spies.pullAndRedecodeTransactions.mockImplementationOnce(
        async (): Promise<void> => new Promise<void>((resolve) => {
          resolveFirst = resolve;
        }),
      );
      spies.pullAndRedecodeTransactions.mockResolvedValueOnce(undefined);

      const conflicts = [
        createMockConflict({ chain: 'ethereum', txHash: '0x111' }),
        createMockConflict({ chain: 'optimism', txHash: '0x222' }),
      ];

      const promise = composable.resolveMany(conflicts, callbacks);
      composable.cancelResolution();
      resolveFirst?.();
      await promise;

      expect(spies.pullAndRedecodeTransactions).toHaveBeenCalledTimes(1);
    });
  });
});
