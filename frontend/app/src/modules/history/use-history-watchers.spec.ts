import type { EffectScope, Ref } from 'vue';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryWatchers } from './use-history-watchers';

const mockProcessing = ref<boolean>(false);
const mockFetchTransactionStatusSummary = vi.fn().mockResolvedValue(undefined);
const mockResetProtocolCacheUpdatesStatus = vi.fn();
const mockProtocolCacheUpdateStatus = ref<Record<string, { cancelled?: boolean }>>({});

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: vi.fn((): { processing: Ref<boolean> } => ({
    processing: mockProcessing,
  })),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: vi.fn((): { fetchTransactionStatusSummary: () => Promise<void> } => ({
    fetchTransactionStatusSummary: mockFetchTransactionStatusSummary,
  })),
}));

vi.mock('@/modules/history/use-protocol-cache-status-store', () => ({
  useProtocolCacheStatusStore: vi.fn((): {
    protocolCacheUpdateStatus: Ref<Record<string, { cancelled?: boolean }>>;
    resetProtocolCacheUpdatesStatus: () => void;
    $id: string;
  } => ({
    $id: 'history/protocol-cache-status',
    protocolCacheUpdateStatus: mockProtocolCacheUpdateStatus,
    resetProtocolCacheUpdatesStatus: mockResetProtocolCacheUpdatesStatus,
  })),
}));

const mockAcknowledgeModifications = vi.fn();
const mockEventsVersion = ref<number>(0);
const mockHasUnprocessedModifications = ref<boolean>(false);

vi.mock('@/modules/history/use-history-store', () => ({
  useHistoryStore: vi.fn(() => {
    const store = reactive({
      acknowledgeModifications: mockAcknowledgeModifications,
      get eventsVersion(): number { return get(mockEventsVersion); },
      hasUnprocessedModifications: mockHasUnprocessedModifications,
    });
    return store;
  }),
}));

const mockTriggerAssetMovementAutoMatching = vi.fn().mockResolvedValue(undefined);

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: vi.fn((): { triggerAssetMovementAutoMatching: () => Promise<void> } => ({
    triggerAssetMovementAutoMatching: mockTriggerAssetMovementAutoMatching,
  })),
}));

const mockTriggerHistoricalBalancesProcessing = vi.fn().mockResolvedValue(undefined);

vi.mock('@/modules/history/balances/use-historical-balances', () => ({
  useHistoricalBalances: vi.fn((): { triggerHistoricalBalancesProcessing: () => Promise<void> } => ({
    triggerHistoricalBalancesProcessing: mockTriggerHistoricalBalancesProcessing,
  })),
}));

const mockRemoveMatching = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn((): { removeMatching: (predicate: (n: unknown) => boolean) => void } => ({
    removeMatching: mockRemoveMatching,
  })),
}));

const mockConnectedExchanges = ref<string[]>([]);

vi.mock('@/modules/settings/use-session-settings-store', () => ({
  useSessionSettingsStore: vi.fn((): {
    connectedExchanges: Ref<string[]>;
    $id: string;
  } => ({
    $id: 'settings/session',
    connectedExchanges: mockConnectedExchanges,
  })),
}));

const mockIsTaskRunning = ref<boolean>(false);

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn((): { useIsTaskRunning: () => Ref<boolean> } => ({
    useIsTaskRunning: vi.fn((): Ref<boolean> => mockIsTaskRunning),
  })),
}));

const mockCurrentRoute = ref<{ path: string }>({ path: '/' });

vi.mock('vue-router', () => ({
  useRouter: vi.fn((): { currentRoute: Ref<{ path: string }> } => ({
    currentRoute: mockCurrentRoute,
  })),
}));

vi.mock('@/modules/core/common/use-ref-debounce', () => ({
  useRefWithDebounce: vi.fn((source: Ref<boolean>, _delay?: number): Ref<boolean> => source),
}));

vi.mock('@shared/utils', () => ({
  startPromise: vi.fn((promise: Promise<unknown>): void => {
    promise.then().catch((error: unknown) => console.error(error));
  }),
}));

vi.mock('es-toolkit', () => ({
  isEqual: vi.fn((a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b)),
}));

describe('useHistoryWatchers', () => {
  let scope: EffectScope;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);

    vi.clearAllMocks();

    set(mockProcessing, false);
    set(mockIsTaskRunning, false);
    set(mockProtocolCacheUpdateStatus, {});
    set(mockEventsVersion, 0);
    set(mockHasUnprocessedModifications, false);
    set(mockConnectedExchanges, []);
    set(mockCurrentRoute, { path: '/' });

    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  function setupWatchers(): void {
    scope.run(() => {
      useHistoryWatchers();
    });
  }

  describe('protocol cache reset watcher', () => {
    it('should reset protocol cache status when task finishes with no cancelled entries', async () => {
      set(mockIsTaskRunning, true);
      set(mockProtocolCacheUpdateStatus, {
        'eth#uniswap': { cancelled: false },
      });

      setupWatchers();
      await nextTick();

      set(mockIsTaskRunning, false);
      await nextTick();

      expect(mockResetProtocolCacheUpdatesStatus).toHaveBeenCalledOnce();
    });

    it('should not reset protocol cache status when task finishes but has cancelled entries', async () => {
      set(mockIsTaskRunning, true);
      set(mockProtocolCacheUpdateStatus, {
        'eth#uniswap': { cancelled: true },
      });

      setupWatchers();
      await nextTick();

      set(mockIsTaskRunning, false);
      await nextTick();

      expect(mockResetProtocolCacheUpdatesStatus).not.toHaveBeenCalled();
    });

    it('should not reset protocol cache status when task is still running', async () => {
      set(mockIsTaskRunning, false);

      setupWatchers();
      await nextTick();

      set(mockIsTaskRunning, true);
      await nextTick();

      expect(mockResetProtocolCacheUpdatesStatus).not.toHaveBeenCalled();
    });
  });

  describe('transaction status summary watcher', () => {
    it('should fetch transaction status summary when processing changes', async () => {
      setupWatchers();
      await nextTick();

      set(mockProcessing, true);
      await nextTick();
      await flushPromises();

      expect(mockFetchTransactionStatusSummary).toHaveBeenCalled();
    });

    it('should fetch transaction status summary when connected exchanges change', async () => {
      setupWatchers();
      await nextTick();

      set(mockConnectedExchanges, ['kraken']);
      await nextTick();
      await flushPromises();

      expect(mockFetchTransactionStatusSummary).toHaveBeenCalled();
    });
  });

  describe('processing debounced watcher', () => {
    it('should acknowledge modifications and trigger reprocessing when processing goes from true to false', async () => {
      set(mockProcessing, true);

      setupWatchers();
      await nextTick();
      await flushPromises();

      vi.clearAllMocks();

      set(mockProcessing, false);
      await nextTick();
      await flushPromises();

      expect(mockAcknowledgeModifications).toHaveBeenCalledOnce();
      expect(mockTriggerHistoricalBalancesProcessing).toHaveBeenCalledOnce();
      expect(mockTriggerAssetMovementAutoMatching).toHaveBeenCalledOnce();
    });

    it('should not trigger reprocessing when processing goes from false to true', async () => {
      setupWatchers();
      await nextTick();

      vi.clearAllMocks();

      set(mockProcessing, true);
      await nextTick();
      await flushPromises();

      expect(mockAcknowledgeModifications).not.toHaveBeenCalled();
      expect(mockTriggerHistoricalBalancesProcessing).not.toHaveBeenCalled();
      expect(mockTriggerAssetMovementAutoMatching).not.toHaveBeenCalled();
    });
  });

  describe('route watcher', () => {
    it('should remove matching notifications when navigating to history events', async () => {
      setupWatchers();
      await nextTick();

      set(mockCurrentRoute, { path: '/history/events' });
      await nextTick();

      expect(mockRemoveMatching).toHaveBeenCalled();
    });

    it('should not remove notifications when navigating to other routes', async () => {
      setupWatchers();
      await nextTick();

      vi.clearAllMocks();

      set(mockCurrentRoute, { path: '/dashboard' });
      await nextTick();

      expect(mockRemoveMatching).not.toHaveBeenCalled();
    });
  });

  describe('debounced events version watcher', () => {
    it('should acknowledge and trigger reprocessing after 15s when events version changes', async () => {
      vi.useFakeTimers();

      set(mockHasUnprocessedModifications, true);

      setupWatchers();
      await nextTick();

      set(mockEventsVersion, 1);
      await nextTick();

      expect(mockAcknowledgeModifications).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(15_000);
      await flushPromises();

      expect(mockAcknowledgeModifications).toHaveBeenCalledOnce();
      expect(mockTriggerHistoricalBalancesProcessing).toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('should not acknowledge when hasUnprocessedModifications is false', async () => {
      vi.useFakeTimers();

      set(mockHasUnprocessedModifications, false);

      setupWatchers();
      await nextTick();

      set(mockEventsVersion, 1);
      await nextTick();

      await vi.advanceTimersByTimeAsync(15_000);
      await flushPromises();

      expect(mockAcknowledgeModifications).not.toHaveBeenCalled();
      expect(mockTriggerHistoricalBalancesProcessing).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });
});
