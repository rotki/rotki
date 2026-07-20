import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeTransactionActions } from '@/modules/history/events/use-bridge-transaction-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    matchBridgeTransactions: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    unlinkBridgeTransaction: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    resolveExternal: vi.fn<(id: number) => Promise<{ message: string; success: boolean }>>()
      .mockResolvedValue({ message: '', success: true }),
    refreshUnmatchedBridgeTransactions: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    showConfirm: vi.fn(),
    showErrorMessage: vi.fn(),
    getChainName: vi.fn((chain: string) => chain.toUpperCase()),
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

vi.mock('@/modules/history/event-utils', () => ({
  getEventEntryFromCollection: <T>(events: T): T => events,
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

    it('should drop the ignored transaction from the current selection', async () => {
      const composable = useBridgeTransactionActions();
      set(composable.modelSelectedUnmatched, ['group1', 'group2']);

      await composable.ignoreTransaction(createMockTransaction({ groupIdentifier: 'group1' }));

      expect(get(composable.modelSelectedUnmatched)).toEqual(['group2']);
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

  describe('confirmMarkExternal', () => {
    it('should show the recorded destination chain and address in the confirmation', () => {
      const transaction = createMockTransaction({
        bridge: { toAddress: '0xdef', toChain: 'optimism' },
      });
      const { confirmMarkExternal } = useBridgeTransactionActions();

      confirmMarkExternal(transaction);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      expect(spies.getChainName).toHaveBeenCalledWith('optimism');
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        message: expect.any(String),
        primaryAction: expect.any(String),
        title: expect.any(String),
      });
    });

    it('should use the recorded source chain and address for a withdrawal confirmation', () => {
      const transaction = createMockTransaction({
        bridge: { fromAddress: '0xabc', fromChain: 'osmosis', toChain: 'ethereum' },
        direction: 'withdrawal',
      });
      const { confirmMarkExternal } = useBridgeTransactionActions();

      confirmMarkExternal(transaction);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      expect(spies.getChainName).toHaveBeenCalledWith('osmosis');
      expect(spies.getChainName).not.toHaveBeenCalledWith('ethereum');
    });

    it('should resolve the deposit as external when the user confirms', async () => {
      const transaction = createMockTransaction({ identifier: 21 });
      const { confirmMarkExternal } = useBridgeTransactionActions();

      confirmMarkExternal(transaction);
      await extractAndCallConfirmCallback();

      expect(spies.resolveExternal).toHaveBeenCalledWith(21);
      expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    });

    it('should not refresh when resolving as external fails', async () => {
      spies.resolveExternal.mockResolvedValueOnce({ message: 'nope', success: false });
      const { confirmMarkExternal } = useBridgeTransactionActions();

      confirmMarkExternal(createMockTransaction());
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
      set(composable.modelSelectedUnmatched, ['g1', 'g3']);
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
      set(composable.modelSelectedIgnored, ['g2']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledTimes(1);
      expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(20);
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
    });
  });
});
