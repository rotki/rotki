import type { Collection } from '@/modules/core/common/collection';
import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import {
  useHistoryEventsViewActions,
  type UseHistoryEventsViewActionsReturn,
} from '@/modules/history/events/use-history-events-view-actions';

const routeQuery = ref<Record<string, unknown>>({});

const { useRouteMock } = vi.hoisted(() => ({ useRouteMock: vi.fn() }));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
}));

const setAvailableIds = vi.fn();
const setTotalMatchingCount = vi.fn();
const fetchDataAndLocations = vi.fn().mockResolvedValue(undefined);
const fetchDataAndRedecode = vi.fn().mockResolvedValue(undefined);
const refreshAll = vi.fn().mockResolvedValue(undefined);
const autoMatchMovement = vi.fn().mockResolvedValue(false);
const refreshUnmatchedAssetMovements = vi.fn().mockResolvedValue(undefined);
const refreshUnmatchedBridgeTransactions = vi.fn().mockResolvedValue(undefined);

const rowA = createMock<HistoryEventRow>({ identifier: 1 });
const rowB = createMock<HistoryEventRow>({ identifier: 2 });

function collection(overrides: Partial<Collection<HistoryEventRow>> = {}): Collection<HistoryEventRow> {
  return createMock<Collection<HistoryEventRow>>({ data: [rowA], found: 1, limit: 10, total: 1, ...overrides });
}

const groups = ref<Collection<HistoryEventRow>>(collection());
const backgroundLoading = ref<boolean>(false);

interface Harness {
  wrapper: VueWrapper;
  view: UseHistoryEventsViewActionsReturn;
}

function mountActions(): Harness {
  let view!: UseHistoryEventsViewActionsReturn;
  const Comp = defineComponent({
    setup(): () => null {
      view = useHistoryEventsViewActions({
        autoMatchMovement,
        backgroundLoading,
        fetchDataAndLocations,
        fetchDataAndRedecode,
        groups,
        refreshAll,
        refreshUnmatchedAssetMovements,
        refreshUnmatchedBridgeTransactions,
        setAvailableIds,
        setTotalMatchingCount,
      });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { view, wrapper };
}

const linkedMovement = createMock<LinkedMovementMatch>({ groupIdentifier: 'group-a', identifier: 9 });

describe('useHistoryEventsViewActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    set(routeQuery, {});
    set(groups, collection());
    set(backgroundLoading, false);
    autoMatchMovement.mockResolvedValue(false);
    useRouteMock.mockReturnValue(computed(() => ({ query: get(routeQuery) })));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  describe('what the table reports about its page', () => {
    it('should hand the event ids to selection mode', () => {
      const { view } = mountActions();

      view.handleUpdateEventIds({ eventIds: [1, 2], groupedEvents: {} });

      expect(setAvailableIds).toHaveBeenCalledWith([1, 2]);
    });

    it('should keep the grouped events a delete needs', () => {
      const { view } = mountActions();
      const groupedEvents = { '0xabc': [rowA, rowB] };

      view.handleUpdateEventIds({ eventIds: [1, 2], groupedEvents });

      expect(get(view.groupedEventsByTxRef)).toStrictEqual(groupedEvents);
    });

    it('should prefer the raw events the table produced', () => {
      const { view } = mountActions();

      view.handleUpdateEventIds({ eventIds: [1], groupedEvents: {}, rawEvents: [rowB] });

      expect(get(view.originalGroups)).toStrictEqual([rowB]);
    });

    it('should fall back to the group page when the table produced none', () => {
      set(groups, collection({ data: [rowA] }));
      const { view } = mountActions();

      view.handleUpdateEventIds({ eventIds: [1], groupedEvents: {} });

      expect(get(view.originalGroups)).toStrictEqual([rowA]);
    });

    it('should treat an empty list of raw events as none', () => {
      set(groups, collection({ data: [rowA] }));
      const { view } = mountActions();

      view.handleUpdateEventIds({ eventIds: [1], groupedEvents: {}, rawEvents: [] });

      // `rawEvents: []` is still a list the table produced, so it wins over the group page.
      expect(get(view.originalGroups)).toStrictEqual([]);
    });
  });

  describe('re-decoding a transaction', () => {
    it('should reload and stop there when nothing is linked to it', async () => {
      const { view } = mountActions();
      const payload = { transactions: [{ location: 'ethereum', txRef: '0xabc' }] };

      await view.handleRedecode(payload);

      expect(fetchDataAndRedecode).toHaveBeenCalledWith(payload);
      expect(autoMatchMovement).not.toHaveBeenCalled();
      expect(fetchDataAndLocations).not.toHaveBeenCalled();
    });

    it('should reload again once a linked movement is matched', async () => {
      autoMatchMovement.mockResolvedValue(true);
      const { view } = mountActions();

      await view.handleRedecode({ linkedMovement, transactions: [{ location: 'ethereum', txRef: '0xabc' }] });

      expect(autoMatchMovement).toHaveBeenCalledWith(linkedMovement);
      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
    });

    it('should not reload again when the linked movement finds no match', async () => {
      const { view } = mountActions();

      await view.handleRedecode({ linkedMovement, transactions: [{ location: 'ethereum', txRef: '0xabc' }] });

      expect(autoMatchMovement).toHaveBeenCalledTimes(1);
      expect(fetchDataAndLocations).not.toHaveBeenCalled();
    });
  });

  describe('reloading after a match', () => {
    it('should re-read the unmatched movements before the events', async () => {
      const { view } = mountActions();

      await view.handleMovementChanged();

      expect(refreshUnmatchedAssetMovements).toHaveBeenCalledTimes(1);
      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
      expect(refreshUnmatchedAssetMovements.mock.invocationCallOrder[0])
        .toBeLessThan(fetchDataAndLocations.mock.invocationCallOrder[0]);
    });

    it('should re-read the unmatched bridge transactions before the events', async () => {
      const { view } = mountActions();

      await view.handleBridgeChanged();

      expect(refreshUnmatchedBridgeTransactions).toHaveBeenCalledTimes(1);
      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
      expect(refreshUnmatchedBridgeTransactions.mock.invocationCallOrder[0])
        .toBeLessThan(fetchDataAndLocations.mock.invocationCallOrder[0]);
    });
  });

  describe('the total the filter matches', () => {
    it('should report it as soon as the page mounts', () => {
      set(groups, collection({ found: 42 }));
      mountActions();

      expect(setTotalMatchingCount).toHaveBeenCalledWith(42);
    });

    it('should report it again when the page changes', async () => {
      mountActions();
      setTotalMatchingCount.mockClear();

      set(groups, collection({ found: 7 }));
      await nextTick();

      expect(setTotalMatchingCount).toHaveBeenCalledWith(7);
    });
  });

  describe('background work finishing', () => {
    it('should reload once it settles', async () => {
      mountActions();
      await vi.advanceTimersByTimeAsync(600);
      fetchDataAndLocations.mockClear();

      set(backgroundLoading, true);
      await nextTick();
      expect(fetchDataAndLocations).not.toHaveBeenCalled();

      set(backgroundLoading, false);
      await nextTick();

      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
    });

    it('should not reload while it is still running', async () => {
      mountActions();
      await vi.advanceTimersByTimeAsync(600);
      fetchDataAndLocations.mockClear();

      set(backgroundLoading, true);
      await nextTick();

      expect(fetchDataAndLocations).not.toHaveBeenCalled();
    });
  });

  describe('the first load', () => {
    it('should wait for the route to settle before refreshing everything', async () => {
      mountActions();

      await nextTick();
      expect(refreshAll).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(600);

      expect(refreshAll).toHaveBeenCalledTimes(1);
    });

    it('should refresh only once, however often the route changes', async () => {
      mountActions();

      set(routeQuery, { asset: 'ETH' });
      await vi.advanceTimersByTimeAsync(600);
      set(routeQuery, { asset: 'BTC' });
      await vi.advanceTimersByTimeAsync(600);

      expect(refreshAll).toHaveBeenCalledTimes(1);
    });

    it('should only reload the events when auto fetch is turned off', async () => {
      vi.stubEnv('VITE_NO_AUTO_FETCH', 'true');
      mountActions();

      await vi.advanceTimersByTimeAsync(600);

      expect(refreshAll).not.toHaveBeenCalled();
      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
    });
  });
});
