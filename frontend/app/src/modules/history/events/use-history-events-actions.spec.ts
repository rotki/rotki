import type { Exchange } from '@/modules/balances/types/exchanges';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { RepullingTransactionResult } from '@/modules/history/events/tx/use-history-transactions';
import { type Blockchain, HistoryEventEntryType, Severity } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { ref, type Ref } from 'vue';
import { useHistoryEventsActions } from './use-history-events-actions';

const mockRefreshTransactions = vi.fn();
const mockCheckMissingEventsAndRedecode = vi.fn();
const mockNotify = vi.fn();
const mockRouterPush = vi.fn();
const mockFetchLocationLabels = vi.fn();
const mockFetchAssociatedLocations = vi.fn();
const mockRedecodeTargeted = vi.fn();

const mockRedecodeTransactions = vi.fn();
const mockShowConfirm = vi.fn();

vi.mock('vue-router', async () => {
  const { ref } = await import('vue');
  return {
    useRoute: vi.fn().mockReturnValue(ref({ query: {} })),
    useRouter: vi.fn(() => ({
      currentRoute: ref({ path: '' }),
      push: mockRouterPush,
    })),
  };
});

vi.mock('@/modules/history/events/tx/use-history-transactions', () => ({
  useHistoryTransactions: vi.fn(() => ({
    refreshTransactions: mockRefreshTransactions,
  })),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => ({
    checkMissingEventsAndRedecode: mockCheckMissingEventsAndRedecode,
    fetchUndecodedTransactionsBreakdown: vi.fn(),
    redecodeTransactions: mockRedecodeTransactions,
  })),
}));

vi.mock('@/modules/history/events/tx/use-targeted-redecode', () => ({
  useTargetedRedecode: vi.fn(() => ({

    redecodeTargeted: mockRedecodeTargeted,
  })),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn(() => ({
    show: mockShowConfirm,
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    resetUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: vi.fn(() => ({
    fetchAssociatedLocations: mockFetchAssociatedLocations,
    fetchLocationLabels: mockFetchLocationLabels,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn(() => ({
    removeMatching: vi.fn(),
  })),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn(() => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/modules/history/events/use-history-events-auto-fetch', () => ({
  useHistoryEventsAutoFetch: vi.fn(),
}));

describe('useHistoryEventsActions', () => {
  function createOptions(): {
    entryTypes: Ref<undefined>;
    refetch: Mock<() => Promise<void>>;
    groups: Ref<Collection<HistoryEventRow>>;
    onlyChains: Ref<Blockchain[]>;
  } {
    return {
      entryTypes: ref(undefined),
      refetch: vi.fn().mockResolvedValue(undefined),
      groups: ref<Collection<HistoryEventRow>>({ data: [], found: 0, limit: 10, total: 0 }),
      onlyChains: ref<Blockchain[]>([]),
    };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    mockRefreshTransactions.mockResolvedValue(undefined);
    mockCheckMissingEventsAndRedecode.mockResolvedValue(undefined);
    mockFetchLocationLabels.mockResolvedValue(undefined);
    mockFetchAssociatedLocations.mockResolvedValue(undefined);
    mockRedecodeTargeted.mockResolvedValue(undefined);
    mockRedecodeTransactions.mockResolvedValue(undefined);
    mockShowConfirm.mockImplementation((_opts, onConfirm) => onConfirm());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('dialogHandlers.onRepullTransactions', () => {
    function createResult(newTransactionsCount: number, newTransactions: Record<string, string[]> = {}): RepullingTransactionResult {
      return { newTransactions, newTransactionsCount };
    }

    it('should call checkMissingEventsAndRedecode', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.(createResult(0));

      expect(mockCheckMissingEventsAndRedecode).toHaveBeenCalled();
    });

    it('should show notification with no transactions message when count is 0', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.(createResult(0));

      expect(mockNotify).toHaveBeenCalledWith({
        action: undefined,
        display: true,
        message: 'actions.repulling_transaction.success.no_tx_description',
        severity: Severity.INFO,
        title: 'actions.repulling_transaction.task.title',
      });
    });

    it('should show notification with count when new transactions found', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.(createResult(5, { eth: ['0xhash1', '0xhash2'] }));

      expect(mockNotify).toHaveBeenCalledWith(expect.objectContaining({
        display: true,
        severity: Severity.INFO,
        title: 'actions.repulling_transaction.task.title',
      }));
      expect(mockNotify.mock.calls[0][0].message).toContain('actions.repulling_transaction.success.description');
      expect(mockNotify.mock.calls[0][0].action).toBeDefined();
    });

    it('should create action that navigates to history events with tx hashes', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.(createResult(2, { eth: ['0xhash1'], optimism: ['0xhash2'] }));

      const notifyCall = mockNotify.mock.calls[0][0];
      expect(notifyCall.action).toBeDefined();

      await notifyCall.action.action();

      expect(mockRouterPush).toHaveBeenCalledWith({
        name: '/history/events/',
        query: {
          txRefs: ['0xhash1', '0xhash2'],
        },
      });
    });
  });

  describe('dialogHandlers.onRepullExchangeEvents', () => {
    it('should call refreshTransactions with exchanges payload', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      const exchanges: Exchange[] = [{ location: 'kraken', name: 'My Kraken' }];
      await dialogHandlers.onRepullExchangeEvents?.(exchanges);

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        disableEvmEvents: true,
        payload: {
          exchanges,
        },
        userInitiated: true,
      });
    });
  });

  describe('redecode paths refresh location labels', () => {
    it('should refresh location labels after evm redecode', async () => {
      const options = createOptions();
      const { redecode } = useHistoryEventsActions(options);

      await redecode.evm({ transactions: [{ location: 'ethereum', txRef: '0xabc' }] });

      expect(mockRedecodeTargeted).toHaveBeenCalled();
      expect(mockFetchLocationLabels).toHaveBeenCalled();
      expect(mockFetchAssociatedLocations).toHaveBeenCalled();
    });

    it('should refresh location labels after block-event redecode', async () => {
      const options = createOptions();
      const { redecode } = useHistoryEventsActions(options);

      await redecode.blocks({ blockNumbers: [123] });

      expect(mockRedecodeTargeted).toHaveBeenCalled();
      expect(mockFetchLocationLabels).toHaveBeenCalled();
      expect(mockFetchAssociatedLocations).toHaveBeenCalled();
    });

    it('should refresh location labels after page redecode with evm events', async () => {
      const options = createOptions();
      set(options.groups, {
        data: [createMock<Extract<HistoryEventEntry, { entryType: typeof HistoryEventEntryType.EVM_EVENT }>>({
          entryType: HistoryEventEntryType.EVM_EVENT,
          location: 'ethereum',
          txRef: '0xabc',
        })],
        found: 1,
        limit: 10,
        total: 1,
      });
      const { redecode } = useHistoryEventsActions(options);

      await redecode.page();

      expect(mockRedecodeTargeted).toHaveBeenCalled();
      expect(mockFetchLocationLabels).toHaveBeenCalled();
      expect(mockFetchAssociatedLocations).toHaveBeenCalled();
    });

    it('should refresh location labels after redecode by chain list', async () => {
      const options = createOptions();
      const { redecode } = useHistoryEventsActions(options);

      await redecode.by({ chains: ['eth'], type: 'chains' });

      expect(mockRedecodeTransactions).toHaveBeenCalledWith(['eth']);
      expect(mockFetchLocationLabels).toHaveBeenCalled();
      expect(mockFetchAssociatedLocations).toHaveBeenCalled();
    });

    it('should refresh location labels after redecode all', async () => {
      const options = createOptions();
      const { redecode } = useHistoryEventsActions(options);

      redecode.all();
      await flushPromises();

      expect(mockShowConfirm).toHaveBeenCalled();
      expect(mockRedecodeTransactions).toHaveBeenCalled();
      expect(mockFetchLocationLabels).toHaveBeenCalled();
      expect(mockFetchAssociatedLocations).toHaveBeenCalled();
    });

    it('should refresh location labels after fetchAndRedecode with payload', async () => {
      const options = createOptions();
      const { fetch } = useHistoryEventsActions(options);

      await fetch.dataAndRedecode({ transactions: [{ location: 'ethereum', txRef: '0xabc' }] });

      expect(mockRedecodeTargeted).toHaveBeenCalled();
      // Exactly once. This used to fetch before the redecode as well as after it, so one action
      // read the table twice and the first read showed pre-redecode data that was immediately
      // replaced. The redecode's own trailing fetch is the only one that can show a result.
      expect(mockFetchLocationLabels).toHaveBeenCalledTimes(1);
      expect(mockFetchAssociatedLocations).toHaveBeenCalledTimes(1);
    });
  });
});
