import type { Ref } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventAction } from '@/modules/history/events/action-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { RepullingTransactionResult } from '@/modules/history/events/tx/use-history-transactions';
import { type Blockchain, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { Routes } from '@/router/routes';
import { useHistoryEventsActions } from './use-history-events-actions';

const mockRefreshTransactions = vi.fn();
const mockCheckMissingEventsAndRedecode = vi.fn();
const mockNotify = vi.fn();
const mockRouterPush = vi.fn();

vi.mock('vue-router', async () => {
  const { ref } = await import('vue');
  return {
    useRoute: vi.fn().mockReturnValue(ref({})),
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
    fetchUndecodedTransactionsStatus: vi.fn(),
    pullAndRecodeEthBlockEvents: vi.fn(),
    pullAndRedecodeTransactions: vi.fn(),
    redecodeTransactions: vi.fn(),
  })),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn(() => ({
    show: vi.fn(),
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    resetUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: vi.fn(() => ({
    fetchAssociatedLocations: vi.fn(),
    fetchLocationLabels: vi.fn(),
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
    currentAction: Ref<HistoryEventAction>;
    entryTypes: Ref<undefined>;
    fetchData: Mock<() => Promise<void>>;
    groups: Ref<Collection<HistoryEventRow>>;
    onlyChains: Ref<Blockchain[]>;
  } {
    return {
      currentAction: ref('query'),
      entryTypes: ref(undefined),
      fetchData: vi.fn().mockResolvedValue(undefined),
      groups: ref<Collection<HistoryEventRow>>({ data: [], found: 0, limit: 10, total: 0 }),
      onlyChains: ref<Blockchain[]>([]),
    };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    mockRefreshTransactions.mockResolvedValue(undefined);
    mockCheckMissingEventsAndRedecode.mockResolvedValue(undefined);
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
        path: Routes.HISTORY_EVENTS.toString(),
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
});
