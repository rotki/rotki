import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeTransactionActions } from '@/modules/history/events/use-bridge-transaction-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    matchBridgeTransactions: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    unlinkBridgeTransaction: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    resolveExternal: vi.fn<(id: number) => Promise<{ message: string; success: boolean }>>()
      .mockResolvedValue({ message: '', success: true }),
    resolveCreateCounterpart: vi.fn<(id: number) => Promise<{ message: string; success: boolean }>>()
      .mockResolvedValue({ message: '', success: true }),
    refreshUnmatchedBridgeTransactions: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    showConfirm: vi.fn(),
    showErrorMessage: vi.fn(),
    getChainName: vi.fn((chain: string) => chain.toUpperCase()),
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

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({
    show: spies.showConfirm,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChainName: spies.getChainName,
  }),
}));

vi.mock('@/modules/history/events/use-untracked-bridge-counterpart', () => ({
  useUntrackedBridgeCounterpart: (): object => ({
    isCounterpartUntracked: spies.isCounterpartUntracked,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (error: unknown): string => error instanceof Error ? error.message : String(error),
  useNotifications: (): object => ({
    showErrorMessage: spies.showErrorMessage,
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
    // The first event of the group is the gas fee event, never the bridge leg, so a
    // regression that falls back to it would send this identifier instead.
    // @ts-expect-error partial mock for testing - only identifier is needed
    events: { entry: { identifier: GAS_FEE_EVENT_IDENTIFIER } },
    identifier: overrides.identifier ?? 1,
    asset: overrides.asset ?? 'ETH',
    bridge: overrides.bridge,
    direction: overrides.direction ?? 'deposit',
  };
}

async function extractAndCallConfirmCallback(): Promise<void> {
  const callback: unknown = spies.showConfirm.mock.calls[0][1];
  if (typeof callback !== 'function')
    throw new Error('Expected callback function');
  await callback();
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

    it('should surface the error and reset ignoreLoading when the request fails', async () => {
      spies.matchBridgeTransactions.mockRejectedValueOnce(new Error('API error'));
      const composable = useBridgeTransactionActions();

      await expect(composable.ignoreTransaction(createMockTransaction())).resolves.toBeUndefined();

      expect(spies.showErrorMessage).toHaveBeenCalledOnce();
      expect(get(composable.ignoreLoading)).toBe(false);
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
    it('should resolve the transaction without asking through a modal', async () => {
      const { markExternal } = useBridgeTransactionActions();

      await markExternal(createMockTransaction({ identifier: 21 }));

      expect(spies.showConfirm).not.toHaveBeenCalled();
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

    // The regression this pair pins: a withdrawal is resolved as income from an untracked
    // source, not as a payment out, and the backend event ends up a receive. Reporting the
    // deposit wording for both directions describes half of them as the opposite transfer.
    it('should describe a resolved withdrawal as income rather than a payment', async () => {
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction({ direction: 'withdrawal' }));

      expect(get(composable.resolutionNotice)).toMatchObject({
        message: 'bridge_matching.resolved.external_withdrawal',
      });
    });

    it('should not refresh or report when resolving as external fails', async () => {
      spies.resolveExternal.mockResolvedValueOnce({ message: 'nope', success: false });
      const composable = useBridgeTransactionActions();

      await composable.markExternal(createMockTransaction());

      expect(spies.refreshUnmatchedBridgeTransactions).not.toHaveBeenCalled();
      expect(get(composable.resolutionNotice)).toBeUndefined();
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

  describe('confirmCreateCounterpart', () => {
    it('should show the counterpart chain of a deposit in the confirmation', () => {
      const transaction = createMockTransaction({
        bridge: { toChain: 'optimism' },
      });
      const { confirmCreateCounterpart } = useBridgeTransactionActions();

      confirmCreateCounterpart(transaction);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        message: 'bridge_matching.actions.create_counterpart_confirm_out_chain::OPTIMISM',
      });
    });

    it('should use the source chain copy for a withdrawal confirmation', () => {
      const transaction = createMockTransaction({
        bridge: { fromChain: 'zksync lite', toChain: 'ethereum' },
        direction: 'withdrawal',
      });
      const { confirmCreateCounterpart } = useBridgeTransactionActions();

      confirmCreateCounterpart(transaction);

      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        message: 'bridge_matching.actions.create_counterpart_confirm_in_chain::ZKSYNC LITE',
      });
    });

    it('should fall back to the chainless copy when no counterpart chain is recorded', () => {
      const { confirmCreateCounterpart } = useBridgeTransactionActions();

      confirmCreateCounterpart(createMockTransaction());

      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        message: 'bridge_matching.actions.create_counterpart_confirm_out',
      });
    });

    it('should create the counterpart when the user confirms', async () => {
      const transaction = createMockTransaction({ identifier: 33 });
      const { confirmCreateCounterpart } = useBridgeTransactionActions();

      confirmCreateCounterpart(transaction);
      await extractAndCallConfirmCallback();

      expect(spies.resolveCreateCounterpart).toHaveBeenCalledWith(33);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });

    it('should not refresh when creating the counterpart fails', async () => {
      spies.resolveCreateCounterpart.mockResolvedValueOnce({ message: 'nope', success: false });
      const { confirmCreateCounterpart } = useBridgeTransactionActions();

      confirmCreateCounterpart(createMockTransaction());
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedBridgeTransactions).not.toHaveBeenCalled();
    });
  });

  describe('confirmIgnoreSelected', () => {
    it('should ignore each selected transaction after confirmation', async () => {
      set(unmatchedTransactionsRef, [
        createMockTransaction({ groupIdentifier: 'g1', identifier: 10 }),
        createMockTransaction({ groupIdentifier: 'g2', identifier: 20 }),
        createMockTransaction({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedUnmatched, ['10', '30']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.matchBridgeTransactions).toHaveBeenCalledTimes(2);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(10);
      expect(spies.matchBridgeTransactions).toHaveBeenCalledWith(30);
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });
  });

  describe('confirmRestoreSelected', () => {
    it('should restore each selected ignored transaction after confirmation', async () => {
      set(ignoredTransactionsRef, [
        createMockTransaction({ groupIdentifier: 'g1', identifier: 10 }),
        createMockTransaction({ groupIdentifier: 'g2', identifier: 20 }),
      ]);

      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedIgnored, ['20']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledTimes(1);
      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(20);
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
    });
  });
});
