import type { KrakenStakingEvents } from '@/modules/staking/staking-types';
import { Zero } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Section, Status } from '@/modules/common/status';
import { useKrakenStakingOperations } from './use-kraken-staking-operations';
import '@test/i18n';

const mockFetchKrakenStakingEvents = vi.fn();
const mockRefreshKrakenStaking = vi.fn();
const mockNotify = vi.fn();
const mockIsTaskRunning = vi.fn().mockReturnValue(false);

vi.mock('@/composables/api/staking/kraken', () => ({
  useKrakenApi: vi.fn(() => ({
    fetchKrakenStakingEvents: mockFetchKrakenStakingEvents,
    refreshKrakenStaking: mockRefreshKrakenStaking,
  })),
}));

vi.mock('@/composables/assets/common', () => ({
  useResolveAssetIdentifier: vi.fn(() => (asset: string): string => asset),
}));

vi.mock('@/modules/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn(() => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/modules/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    removeMatching: vi.fn(),
  }),
}));

vi.mock('@/modules/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn(() => ({
    runTask: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>): Promise<unknown> => {
      await taskFn();
      return { success: true, result: {} };
    }),
  })),
}));

vi.mock('@/modules/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({
    isTaskRunning: mockIsTaskRunning,
  })),
}));

vi.mock('@/modules/settings/use-frontend-settings-store', () => ({
  useFrontendSettingsStore: vi.fn(() => reactive({ itemsPerPage: 10 })),
}));

function defaultEvents(): KrakenStakingEvents {
  return {
    assets: [],
    entriesFound: 0,
    entriesLimit: 0,
    entriesTotal: 0,
    received: [],
    totalValue: Zero,
  };
}

describe('useKrakenStakingOperations', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.clearAllMocks();
    mockIsTaskRunning.mockReturnValue(false);
  });

  afterEach(() => {
    scope.stop();
    vi.clearAllMocks();
  });

  describe('fetchEvents', () => {
    it('should set status to LOADED on first load error', async () => {
      const { useStatusStore } = await import('@/modules/common/use-status-store');

      mockFetchKrakenStakingEvents.mockRejectedValueOnce(new Error('Request timeout'));

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const statusStore = useStatusStore();

      await fetchEvents();

      const status = statusStore.getStatus(Section.STAKING_KRAKEN);
      expect(status).toBe(Status.LOADED);
      expect(mockNotify).toHaveBeenCalledOnce();
    });

    it('should load events successfully on first load', async () => {
      const { useStatusStore } = await import('@/modules/common/use-status-store');

      const eventsData = {
        ...defaultEvents(),
        entriesFound: 1,
        entriesTotal: 1,
      };

      mockFetchKrakenStakingEvents.mockResolvedValue(eventsData);
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const statusStore = useStatusStore();

      await fetchEvents();

      const status = statusStore.getStatus(Section.STAKING_KRAKEN);
      expect(status).toBe(Status.LOADED);
      expect(mockNotify).not.toHaveBeenCalled();
    });

    it('should set status to LOADED when refresh task fails', async () => {
      const { useStatusStore } = await import('@/modules/common/use-status-store');

      mockFetchKrakenStakingEvents.mockResolvedValueOnce(defaultEvents());
      mockRefreshKrakenStaking.mockRejectedValueOnce(new Error('Backend unresponsive'));

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const statusStore = useStatusStore();

      await fetchEvents();

      const status = statusStore.getStatus(Section.STAKING_KRAKEN);
      expect(status).toBe(Status.LOADED);
      expect(mockNotify).toHaveBeenCalledOnce();
    });

    it('should skip when task is already running', async () => {
      mockIsTaskRunning.mockReturnValue(true);

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      await fetchEvents();

      expect(mockFetchKrakenStakingEvents).not.toHaveBeenCalled();
    });

    it('should fetch events with date filter', async () => {
      mockFetchKrakenStakingEvents.mockResolvedValue(defaultEvents());
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const dateFilter = { fromTimestamp: 1000, toTimestamp: 2000 };

      await fetchEvents(false, dateFilter);

      const lastCallArgs = mockFetchKrakenStakingEvents.mock.calls.at(-1)?.[0];
      expect(lastCallArgs).toMatchObject(dateFilter);
    });

    it('should call refreshEvents on explicit refresh', async () => {
      const { useStatusStore } = await import('@/modules/common/use-status-store');
      const statusStore = useStatusStore();

      // Pre-set status to LOADED so isFirstLoad() returns false
      statusStore.setStatus({ status: Status.LOADED, section: Section.STAKING_KRAKEN });

      mockFetchKrakenStakingEvents.mockResolvedValue(defaultEvents());
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      await fetchEvents(true);

      expect(mockRefreshKrakenStaking).toHaveBeenCalledOnce();
    });
  });

  describe('updatePagination', () => {
    it('should update pagination and fetch events', async () => {
      mockFetchKrakenStakingEvents.mockResolvedValue(defaultEvents());
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { updatePagination } = scope.run(() => useKrakenStakingOperations())!;

      await updatePagination({
        ascending: [true],
        limit: 25,
        offset: 0,
        orderByAttributes: ['timestamp'],
      });

      expect(mockFetchKrakenStakingEvents).toHaveBeenCalled();
    });
  });
});
