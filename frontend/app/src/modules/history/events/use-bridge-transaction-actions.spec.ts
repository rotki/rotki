import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeTransactionActions } from '@/modules/history/events/use-bridge-transaction-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    matchBridgeTransactions: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    unlinkBridgeTransaction: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    resolveExternal: vi.fn<(id: number) => Promise<{ message: unknown; success: boolean }>>()
      .mockResolvedValue({ message: '', success: true }),
    resolveCreateCounterpart: vi.fn<(id: number) => Promise<{ message: unknown; success: boolean }>>()
      .mockResolvedValue({ message: '', success: true }),
    refreshUnmatchedBridgeTransactions: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    isCounterpartUntracked: vi.fn<() => boolean>(() => false),
  },
}));

const unmatchedTransactionsRef = ref<UnmatchedBridgeTransaction[]>([]);
const ignoredTransactionsRef = ref<UnmatchedBridgeTransaction[]>([]);

vi.mock('@/modules/history/api/events/use-bridge-matching-api', () => ({
  useBridgeMatchingApi: (): object => ({
    matchBridgeTransactions: spies.matchBridgeTransactions,
    unlinkBridgeTransaction: spies.unlinkBridgeTransaction,
  }),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({
    unmatchedTransactions: computed<UnmatchedBridgeTransaction[]>(() => get(unmatchedTransactionsRef)),
    ignoredTransactions: computed<UnmatchedBridgeTransaction[]>(() => get(ignoredTransactionsRef)),
    refreshUnmatchedBridgeTransactions: spies.refreshUnmatchedBridgeTransactions,
    resolveCreateCounterpart: spies.resolveCreateCounterpart,
    resolveExternal: spies.resolveExternal,
  }),
}));

vi.mock('@/modules/history/events/use-untracked-bridge-counterpart', () => ({
  useUntrackedBridgeCounterpart: (): object => ({
    isCounterpartUntracked: spies.isCounterpartUntracked,
  }),
}));

const GAS_FEE_EVENT_IDENTIFIER = 999;

function createMockTransaction(overrides: {
  groupIdentifier?: string;
  identifier?: number;
  asset?: string;
  direction?: 'deposit' | 'withdrawal';
  bridge?: UnmatchedBridgeTransaction['bridge'];
} = {}): UnmatchedBridgeTransaction {
  return {
    groupIdentifier: overrides.groupIdentifier ?? 'group1',
    // @ts-expect-error partial mock for testing - only identifier is needed
    events: { entry: { identifier: GAS_FEE_EVENT_IDENTIFIER } },
    identifier: overrides.identifier ?? 1,
    asset: overrides.asset ?? 'ETH',
    bridge: overrides.bridge,
    direction: overrides.direction ?? 'deposit',
  };
}

describe('use-bridge-transaction-actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(unmatchedTransactionsRef, []);
    set(ignoredTransactionsRef, []);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('ignoreTransaction', () => {
    it('should mark the transaction as a no-match with its identifier', async () => {
      const transaction = createMockTransaction({ identifier: 42 });
      const { ignoreTransaction } = useBridgeTransactionActions();

      await ignoreTransaction(transaction);

      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(42);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });

    it('should call onActionComplete on success', async () => {
      const onActionComplete = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
      const { ignoreTransaction } = useBridgeTransactionActions({ onActionComplete });

      await ignoreTransaction(createMockTransaction());

      expect(onActionComplete).toHaveBeenCalledOnce();
    });

    it('should keep the failure for the panel instead of a dialog, and reset ignoreLoading', async () => {
      const failure = new Error('API error');
      spies.matchBridgeTransactions.mockRejectedValueOnce(failure);
      const composable = useBridgeTransactionActions();

      await expect(composable.ignoreTransaction(createMockTransaction())).resolves.toBeUndefined();

      expect(get(composable.actionFailure)).toBe(failure);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should clear the kept failure when the next action starts', async () => {
      spies.matchBridgeTransactions.mockRejectedValueOnce(new Error('API error'));
      const composable = useBridgeTransactionActions();
      await composable.ignoreTransaction(createMockTransaction());

      await composable.ignoreTransaction(createMockTransaction());

      expect(get(composable.actionFailure)).toBeUndefined();
    });

    it('should report the ignore in place, with an undo that restores it', async () => {
      const composable = useBridgeTransactionActions();

      await composable.ignoreTransaction(createMockTransaction({ identifier: 42 }));

      expect(get(composable.resolutionNotice)).toMatchObject({
        message: 'bridge_matching.resolved.ignored',
      });

      await composable.undoResolution();

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(42);
    });

    it('should drop the ignored leg from the current selection', async () => {
      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedUnmatched, ['42', '55']);

      await composable.ignoreTransaction(createMockTransaction({ identifier: 42 }));

      expect(get(composable.modelSelectedUnmatched)).toEqual(['55']);
    });

    it('should not use the gas fee event of the group as the bridge identifier', async () => {
      const { ignoreTransaction } = useBridgeTransactionActions();

      await ignoreTransaction(createMockTransaction({ identifier: 42 }));

      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(42);
      expect(spies.matchBridgeTransactions).not.toHaveBeenCalledWith(GAS_FEE_EVENT_IDENTIFIER);
    });
  });

  describe('restoreTransaction', () => {
    it('should unlink the transaction with its identifier', async () => {
      const transaction = createMockTransaction({ identifier: 55 });
      const { restoreTransaction } = useBridgeTransactionActions();

      await restoreTransaction(transaction);

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(55);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });
  });

  describe('markExternal', () => {
    it('should resolve the transaction straight away', async () => {
      const { markExternal } = useBridgeTransactionActions();

      await markExternal(createMockTransaction({ identifier: 21 }));

      expect(spies.resolveExternal).toHaveBeenCalledWith(21);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });

    it('should report the result in place, with an undo that unlinks it again', async () => {
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction({ identifier: 21 }));

      expect(get(composable.resolutionNotice)).toMatchObject({
        message: 'bridge_matching.resolved.external_deposit',
      });

      await composable.undoResolution();

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(21);
      expect(get(composable.resolutionNotice)).toBeUndefined();
    });

    it('should describe a resolved withdrawal as income rather than a payment', async () => {
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction({ direction: 'withdrawal' }));

      expect(get(composable.resolutionNotice)).toMatchObject({
        message: 'bridge_matching.resolved.external_withdrawal',
      });
    });

    it('should keep a refused resolution for the panel, without refreshing or leaving a notice', async () => {
      const failure = new Error('nope');
      spies.resolveExternal.mockResolvedValueOnce({ message: failure, success: false });
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction());

      expect(get(composable.actionFailure)).toBe(failure);
      expect(spies.refreshUnmatchedBridgeTransactions).not.toHaveBeenCalled();
      expect(get(composable.resolutionNotice)).toBeUndefined();
    });

    it('should name a refresh that fails after the leg was resolved, instead of rejecting unhandled', async () => {
      const failure = new Error('refresh failed');
      spies.refreshUnmatchedBridgeTransactions.mockRejectedValueOnce(failure);
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction());

      expect(get(composable.actionFailure)).toBe(failure);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should drop the notice once the leg it describes is restored from its row', async () => {
      const composable = useBridgeTransactionActions();
      const transaction = createMockTransaction({ identifier: 21 });

      await composable.markExternal(transaction);
      await composable.restoreTransaction(transaction);

      expect(get(composable.resolutionNotice)).toBeUndefined();
    });

    it('should keep the notice when an unrelated leg is restored', async () => {
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction({ identifier: 21 }));
      await composable.restoreTransaction(createMockTransaction({ identifier: 99 }));

      expect(get(composable.resolutionNotice)).toBeDefined();
    });

    it('should drop the notice when it is dismissed', async () => {
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction());
      composable.dismissResolution();

      expect(get(composable.resolutionNotice)).toBeUndefined();
      expect(spies.unlinkBridgeTransaction).not.toHaveBeenCalled();
    });
  });

  describe('createCounterpart', () => {
    it('should create the counterpart of the leg its row confirmed', async () => {
      const transaction = createMockTransaction({ identifier: 33 });
      const { createCounterpart } = useBridgeTransactionActions();

      await createCounterpart(transaction);

      expect(spies.resolveCreateCounterpart).toHaveBeenCalledWith(33);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });

    it('should keep a refused counterpart for the panel, without refreshing', async () => {
      const failure = new Error('nope');
      spies.resolveCreateCounterpart.mockResolvedValueOnce({ message: failure, success: false });
      const { actionFailure, createCounterpart } = useBridgeTransactionActions();

      await createCounterpart(createMockTransaction());

      expect(get(actionFailure)).toBe(failure);
      expect(spies.refreshUnmatchedBridgeTransactions).not.toHaveBeenCalled();
    });

    it('should name a refresh that fails after the counterpart was created', async () => {
      const failure = new Error('refresh failed');
      spies.refreshUnmatchedBridgeTransactions.mockRejectedValueOnce(failure);
      const { actionFailure, createCounterpart } = useBridgeTransactionActions();

      await createCounterpart(createMockTransaction());

      expect(get(actionFailure)).toBe(failure);
    });
  });

  describe('ignoreSelected', () => {
    it('should count the selection in the question its button asks', () => {
      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedUnmatched, ['10', '30']);

      expect(get(composable.ignoreSelectedQuestion)).toEqual({
        confirmLabel: 'asset_movement_matching.dialog.ignore',
        message: 'bridge_matching.actions.ignore_selected_confirm::2',
        title: 'bridge_matching.actions.ignore_selected',
      });
    });

    it('should ignore each selected transaction', async () => {
      set(unmatchedTransactionsRef, [
        createMockTransaction({ groupIdentifier: 'g1', identifier: 10 }),
        createMockTransaction({ groupIdentifier: 'g2', identifier: 20 }),
        createMockTransaction({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedUnmatched, ['10', '30']);
      await composable.ignoreSelected();

      expect(spies.matchBridgeTransactions).toHaveBeenCalledTimes(2);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(10);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(30);
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });
  });

  describe('restoreSelected', () => {
    it('should restore each selected ignored transaction without asking', async () => {
      set(ignoredTransactionsRef, [
        createMockTransaction({ groupIdentifier: 'g1', identifier: 10 }),
        createMockTransaction({ groupIdentifier: 'g2', identifier: 20 }),
      ]);

      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedIgnored, ['20']);
      await composable.restoreSelected();

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledTimes(1);
      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(20);
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
    });
  });
});
