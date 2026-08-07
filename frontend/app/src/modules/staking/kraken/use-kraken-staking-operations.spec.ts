import type { KrakenStakingEvents } from '@/modules/staking/staking-types';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { Zero } from '@rotki/common';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useKrakenStakingOperations } from './use-kraken-staking-operations';
import '@test/i18n';

const mockFetchKrakenStakingEvents = vi.fn();
const mockRefreshKrakenStaking = vi.fn();
const mockNotify = vi.fn();
const { mockCancelPendingEventReads } = vi.hoisted(() => ({ mockCancelPendingEventReads: vi.fn() }));

const IDLE: WorkStatus = { active: false, everCompleted: false, pending: false, running: false };
let workStatus: WorkStatus = { ...IDLE };
const statusOf = vi.fn((): WorkStatus => workStatus);

vi.mock('@/modules/staking/api/use-kraken-api', () => ({
  useKrakenApi: vi.fn(() => ({
    cancelPendingEventReads: mockCancelPendingEventReads,
    fetchKrakenStakingEvents: mockFetchKrakenStakingEvents,
    refreshKrakenStaking: mockRefreshKrakenStaking,
  })),
}));

vi.mock('@/modules/assets/use-resolve-asset-identifier', () => ({
  useResolveAssetIdentifier: vi.fn(() => (asset: string): string => asset),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn(() => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    removeMatching: vi.fn(),
  }),
}));

// The native `run` invokes the api call (so a rejecting refresh still surfaces) and yields a
// plainfp Result; `submitTask` runs the spec inline so the real `run` body drives assertions.
const { runTask } = vi.hoisted(() => ({ runTask: vi.fn() }));

vi.mock('@/modules/task-center/use-native-task', async () => {
  const { ok } = await import('plainfp/result');
  runTask.mockImplementation(async (task: () => Promise<unknown>) => {
    await task();
    return ok(undefined);
  });

  return {
    useNativeTask: vi.fn(() => ({
      statusOf,
      submitTask: vi.fn(runSpecWith(runTask)),
    })),
  };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'itemsPerPage' ? ref(10) : ref(undefined))),
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
    workStatus = { ...IDLE };
  });

  afterEach(() => {
    scope.stop();
    vi.clearAllMocks();
  });

  describe('fetchEvents', () => {
    it('should stop loading on first load error', async () => {
      const { useKrakenStakingStore } = await import('@/modules/staking/use-kraken-staking-store');

      mockFetchKrakenStakingEvents.mockRejectedValueOnce(new Error('Request timeout'));

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const store = useKrakenStakingStore();

      await fetchEvents();

      expect(get(store.loading)).toBe(false);
      expect(mockNotify).toHaveBeenCalledOnce();
    });

    it('should load events successfully on first load', async () => {
      const { useKrakenStakingStore } = await import('@/modules/staking/use-kraken-staking-store');

      const eventsData = {
        ...defaultEvents(),
        entriesFound: 1,
        entriesTotal: 1,
      };

      mockFetchKrakenStakingEvents.mockResolvedValue(eventsData);
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const store = useKrakenStakingStore();

      await fetchEvents();

      expect(get(store.loading)).toBe(false);
      expect(get(store.loadedOnce)).toBe(true);
      expect(mockNotify).not.toHaveBeenCalled();
    });

    it('should stop loading when the refresh task fails', async () => {
      const { useKrakenStakingStore } = await import('@/modules/staking/use-kraken-staking-store');

      mockFetchKrakenStakingEvents.mockResolvedValueOnce(defaultEvents());
      mockRefreshKrakenStaking.mockRejectedValueOnce(new Error('Backend unresponsive'));

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const store = useKrakenStakingStore();

      await fetchEvents();

      expect(get(store.loading)).toBe(false);
      expect(mockNotify).toHaveBeenCalledOnce();
    });

    it('should skip when the refresh activity is already running', async () => {
      workStatus = { ...IDLE, active: true, running: true };

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

    it('should cancel a read still in flight before starting a new one', async () => {
      mockFetchKrakenStakingEvents.mockResolvedValue(defaultEvents());
      mockRefreshKrakenStaking.mockResolvedValue({ taskId: 1 });

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      await fetchEvents(false, { fromTimestamp: 1000 });

      expect(mockCancelPendingEventReads).toHaveBeenCalledOnce();
      // Cancelling has to precede the read it supersedes, or the read it aborts is its own.
      expect(mockCancelPendingEventReads.mock.invocationCallOrder[0])
        .toBeLessThan(mockFetchKrakenStakingEvents.mock.invocationCallOrder[0]);
    });

    it('should leave loading alone when a read is cancelled', async () => {
      const { useKrakenStakingStore } = await import('@/modules/staking/use-kraken-staking-store');
      const { RequestCancelledError } = await import('@/modules/core/api/request-queue/errors');

      mockFetchKrakenStakingEvents.mockRejectedValueOnce(new RequestCancelledError('superseded'));

      const { fetchEvents } = scope.run(() => useKrakenStakingOperations())!;
      const store = useKrakenStakingStore();

      await fetchEvents();

      // The read that replaced this one owns `loading`; clearing it here would hide the spinner
      // while that newer read is still running.
      expect(get(store.loading)).toBe(true);
      expect(mockNotify).not.toHaveBeenCalled();
    });

    it('should call refreshEvents on explicit refresh', async () => {
      const { useKrakenStakingStore } = await import('@/modules/staking/use-kraken-staking-store');

      // Mark it already loaded so the explicit-refresh path, not the first-load path, is exercised.
      const { loadedOnce } = storeToRefs(useKrakenStakingStore());
      set(loadedOnce, true);

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
