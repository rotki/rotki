import type { Ref } from 'vue';
import type { RepullingTransactionResult } from '@/composables/history/events/tx';
import type { HistoryEventAction } from '@/composables/history/events/types';
import type { Collection } from '@/types/collection';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Blockchain, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { Routes } from '@/router/routes';
import { useHistoryEventsActions } from './use-history-events-actions';

const mockRefreshTransactions = vi.fn();
const mockCheckMissingEventsAndRedecode = vi.fn();
const mockNotify = vi.fn();
const mockRouterPush = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: mockRouterPush,
  })),
}));

vi.mock('@/composables/history/events/tx', () => ({
  useHistoryTransactions: vi.fn(() => ({
    refreshTransactions: mockRefreshTransactions,
  })),
}));

vi.mock('@/composables/history/events/tx/decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => ({
    checkMissingEventsAndRedecode: mockCheckMissingEventsAndRedecode,
    fetchUndecodedTransactionsStatus: vi.fn(),
    pullAndRecodeEthBlockEvents: vi.fn(),
    pullAndRedecodeTransactions: vi.fn(),
    redecodeTransactions: vi.fn(),
  })),
}));

vi.mock('@/composables/history/events/mapping', () => ({
  useHistoryEventMappings: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock('@/store/confirm', () => ({
  useConfirmStore: vi.fn(() => ({
    show: vi.fn(),
  })),
}));

vi.mock('@/store/history', () => ({
  useHistoryStore: vi.fn(() => ({
    fetchAssociatedLocations: vi.fn(),
    fetchLocationLabels: vi.fn(),
    resetUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
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

      const exchanges = [{ location: 'kraken', name: 'My Kraken' }];
      await dialogHandlers.onRepullExchangeEvents?.(exchanges as any);

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
