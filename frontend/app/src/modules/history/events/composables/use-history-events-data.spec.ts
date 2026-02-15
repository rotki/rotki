import type { Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestCancelledError } from '@/modules/api/request-queue/errors';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/types/history/events/schemas';

const mockItemsPerPage = ref<number>(10);

// Mock external dependencies
const mockFetchHistoryEvents = vi.fn();
const mockIsAssetIgnored = vi.fn();
const mockCancelByTag = vi.fn();

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(() => ({
    fetchHistoryEvents: mockFetchHistoryEvents,
  })),
}));

vi.mock('@/modules/api/rotki-api', () => ({
  api: {
    cancelByTag: (...args: any[]): void => mockCancelByTag(...args),
  },
}));

vi.mock('@/composables/ref', () => ({
  useRefWithDebounce: vi.fn((value: Ref<boolean>) => value),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: vi.fn(() => ({
    sectionLoading: computed<boolean>(() => false),
  })),
}));

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn(() => ({
    isAssetIgnored: mockIsAssetIgnored,
  })),
}));

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn(() => ({
    itemsPerPage: mockItemsPerPage,
  })),
}));

vi.mock('@/utils/collection', () => ({
  getCollectionData: vi.fn((groups: Ref<Collection<HistoryEventRow>>) => ({
    data: computed<HistoryEventRow[]>(() => get(groups).data),
    entriesFoundTotal: computed<number | undefined>(() => undefined),
    found: computed<number>(() => get(groups).found),
    limit: computed<number>(() => get(groups).limit),
    total: computed<number>(() => get(groups).total),
  })),
  setupEntryLimit: vi.fn(() => ({
    showUpgradeRow: computed<boolean>(() => false),
  })),
}));

describe('use-history-events-data', () => {
  function createMockEvent(overrides: Omit<Partial<HistoryEventEntry>, 'entryType'> = {}): HistoryEventEntry {
    const event: HistoryEventEntry = {
      address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
      amount: bigNumberify('100'),
      asset: 'ETH',
      counterparty: null,
      states: [],
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
      eventSubtype: 'spend',
      eventType: 'transfer',
      extraData: null,
      groupIdentifier: 'group1',
      hidden: false,
      identifier: 1,
      ignoredInAccounting: false,
      location: 'ethereum',
      locationLabel: 'Account 1',
      sequenceIndex: 0,
      timestamp: 1000000,
      txRef: 'tx1',
    };
    return { ...event, ...overrides };
  }

  function createMockCollection(data: HistoryEventRow[]): Collection<HistoryEventRow> {
    return {
      data,
      found: data.length,
      limit: 10,
      total: data.length,
    };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    mockFetchHistoryEvents.mockResolvedValue({ data: [] });
    mockIsAssetIgnored.mockReturnValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('groups flattening', () => {
    it('should flatten groups from collection data', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1, event2]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(get(result.groups)).toHaveLength(2);
      expect(get(result.groups)[0]).toEqual(event1);
      expect(get(result.groups)[1]).toEqual(event2);
    });

    it('should flatten nested array groups', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const nestedGroup = [event1, event2];

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([nestedGroup]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(get(result.groups)).toHaveLength(2);
    });
  });

  describe('loading states', () => {
    it('should expose loading state from groupLoading', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([]));
      const groupLoading = ref<boolean>(true);
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading,
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(get(result.loading)).toBe(true);

      set(groupLoading, false);
      await nextTick();

      expect(get(result.loading)).toBe(false);
    });

    it('should expose eventsLoading ref', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(result.eventsLoading).toBeDefined();
    });
  });

  describe('empty state handling', () => {
    it('should return empty mapping when groups is empty', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await nextTick();

      expect(get(result.completeEventsMapped)).toEqual({});
      expect(get(result.displayedEventsMapped)).toEqual({});
    });

    it('should return empty arrays for groups and events when collection is empty', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(get(result.groups)).toEqual([]);
      expect(get(result.events)).toEqual([]);
    });
  });

  describe('collection metadata', () => {
    it('should expose found, limit, and total from collection', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ identifier: 1 });
      const collection: Collection<HistoryEventRow> = {
        data: [event1],
        found: 100,
        limit: 10,
        total: 500,
      };

      const groups = ref<Collection<HistoryEventRow>>(collection);
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(get(result.found)).toBe(100);
      expect(get(result.limit)).toBe(10);
      expect(get(result.total)).toBe(500);
    });
  });

  describe('async event fetching and mapping', () => {
    async function waitForFetchEvents(): Promise<void> {
      // Wait for the watchImmediate callback and its async fetchEvents() to resolve
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
    }

    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should call fetchHistoryEvents with correct groupIdentifiers', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [event1, event2] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1, event2]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      expect(mockFetchHistoryEvents).toHaveBeenCalledWith(
        expect.objectContaining({
          groupIdentifiers: ['group1', 'group2'],
          limit: -1,
          offset: 0,
        }),
        expect.objectContaining({
          tags: ['history-events-detail'],
        }),
      );
    });

    it('should map events by groupIdentifier in completeEventsMapped', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const event3 = createMockEvent({ groupIdentifier: 'group2', identifier: 3 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [event1, event2, event3] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1, event3]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const mapped = get(result.completeEventsMapped);
      expect(mapped.group1).toHaveLength(2);
      expect(mapped.group2).toHaveLength(1);
    });

    it('should filter hidden events from mapping', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const visibleEvent = createMockEvent({ groupIdentifier: 'group1', hidden: false, identifier: 1 });
      const hiddenEvent = createMockEvent({ groupIdentifier: 'group1', hidden: true, identifier: 2 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [visibleEvent, hiddenEvent] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([visibleEvent]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const mapped = get(result.completeEventsMapped);
      expect(mapped.group1).toHaveLength(1);
      expect(mapped.group1[0]).toEqual(visibleEvent);
    });

    it('should return same mapping when excludeIgnored is false', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [event1] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      expect(get(result.displayedEventsMapped)).toEqual(get(result.completeEventsMapped));
    });

    it('should filter ignored assets when excludeIgnored is true', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const ethEvent = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });
      const btcEvent = createMockEvent({ asset: 'BTC', groupIdentifier: 'group1', identifier: 2 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [ethEvent, btcEvent] });
      mockIsAssetIgnored.mockImplementation((asset: string) => asset === 'BTC');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([ethEvent]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const displayed = get(result.displayedEventsMapped);
      expect(displayed.group1).toHaveLength(1);
      expect(displayed.group1[0]).toEqual(ethEvent);
    });

    it('should exclude groups entirely when all events are ignored', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const btcEvent = createMockEvent({ asset: 'BTC', groupIdentifier: 'group1', identifier: 1 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [btcEvent] });
      mockIsAssetIgnored.mockReturnValue(true);

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([btcEvent]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const displayed = get(result.displayedEventsMapped);
      expect(displayed.group1).toBeUndefined();
    });

    it('should detect hidden ignored assets inside swap subgroups', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const approveEvent = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });
      const swapSpend = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 2 });
      const swapReceive = createMockEvent({ asset: 'SPAM_TOKEN', groupIdentifier: 'group1', identifier: 3 });

      // API returns: approve + [swapSpend, swapReceive] as a subgroup
      const swapSubgroup: HistoryEventRow = [swapSpend, swapReceive];
      mockFetchHistoryEvents.mockResolvedValue({ data: [approveEvent, swapSubgroup] });
      mockIsAssetIgnored.mockImplementation((asset: string) => asset === 'SPAM_TOKEN');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([approveEvent]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      // completeEventsMapped should have 3 events (approve + 2 in subgroup)
      const complete = get(result.completeEventsMapped);
      expect(complete.group1).toHaveLength(2); // [approveEvent, [swapSpend, swapReceive]]

      // displayedEventsMapped should filter out SPAM_TOKEN from the subgroup
      const displayed = get(result.displayedEventsMapped);
      expect(displayed.group1).toHaveLength(2); // [approveEvent, [swapSpend]]

      // The group should be detected as having hidden ignored assets
      expect(get(result.groupsWithHiddenIgnoredAssets).has('group1')).toBe(true);
    });

    it('should not flag group when no assets are ignored inside subgroups', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const swapSpend = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });
      const swapReceive = createMockEvent({ asset: 'USDC', groupIdentifier: 'group1', identifier: 2 });

      const swapSubgroup: HistoryEventRow = [swapSpend, swapReceive];
      mockFetchHistoryEvents.mockResolvedValue({ data: [swapSubgroup] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([swapSpend]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      expect(get(result.groupsWithHiddenIgnoredAssets).has('group1')).toBe(false);
    });
  });

  describe('cancellation and stale response protection', () => {
    async function waitForFetchEvents(): Promise<void> {
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
    }

    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should call api.cancelByTag before each fetch', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      mockFetchHistoryEvents.mockResolvedValue({ data: [event1] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      expect(mockCancelByTag).toHaveBeenCalledWith('history-events-detail');
    });

    it('should discard stale response when a newer fetch has started', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });

      // First call: slow, resolves after second call completes
      let resolveFirst: ((value: { data: HistoryEventRow[] }) => void) | undefined;
      const firstPromise = new Promise<{ data: HistoryEventRow[] }>((resolve) => {
        resolveFirst = resolve;
      });

      mockFetchHistoryEvents
        .mockReturnValueOnce(firstPromise)
        .mockResolvedValueOnce({ data: [event2] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      // Let the first (immediate) fetch start
      await nextTick();

      // Trigger a second fetch by changing groups
      set(groups, createMockCollection([event2]));
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();

      // Now resolve the first (stale) promise
      resolveFirst!({ data: [event1] });
      await vi.runAllTimersAsync();
      await nextTick();

      // The events should contain data from the second (newer) fetch, not the stale first
      const rawEvents = get(result.rawEvents);
      expect(rawEvents).toHaveLength(1);
      expect(rawEvents[0]).toEqual(event2);
    });

    it('should handle RequestCancelledError silently without clearing events', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      // First call succeeds
      mockFetchHistoryEvents.mockResolvedValueOnce({ data: [event1] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();
      expect(get(result.rawEvents)).toHaveLength(1);

      // Second call throws RequestCancelledError
      mockFetchHistoryEvents.mockRejectedValueOnce(new RequestCancelledError());

      // Trigger a new fetch by changing groups
      const event2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });
      set(groups, createMockCollection([event2]));
      await waitForFetchEvents();

      // Previous data should be preserved (not cleared)
      expect(get(result.rawEvents)).toHaveLength(1);
      expect(get(result.rawEvents)[0]).toEqual(event1);
    });

    it('should set eventsLoading during fetch and reset after', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      let resolvePromise: ((value: { data: HistoryEventRow[] }) => void) | undefined;
      mockFetchHistoryEvents.mockReturnValue(new Promise<{ data: HistoryEventRow[] }>((resolve) => {
        resolvePromise = resolve;
      }));

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      // After immediate watch fires, eventsLoading should be true
      await nextTick();
      expect(get(result.eventsLoading)).toBe(true);

      // Resolve the fetch
      resolvePromise!({ data: [event1] });
      await vi.runAllTimersAsync();
      await nextTick();

      expect(get(result.eventsLoading)).toBe(false);
    });

    it('should not reset eventsLoading when a stale fetch completes', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });

      let resolveFirst: ((value: { data: HistoryEventRow[] }) => void) | undefined;
      const firstPromise = new Promise<{ data: HistoryEventRow[] }>((resolve) => {
        resolveFirst = resolve;
      });

      let resolveSecond: ((value: { data: HistoryEventRow[] }) => void) | undefined;
      const secondPromise = new Promise<{ data: HistoryEventRow[] }>((resolve) => {
        resolveSecond = resolve;
      });

      mockFetchHistoryEvents
        .mockReturnValueOnce(firstPromise)
        .mockReturnValueOnce(secondPromise);

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      // Let first fetch start
      await nextTick();
      expect(get(result.eventsLoading)).toBe(true);

      // Trigger second fetch
      set(groups, createMockCollection([event2]));
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();

      // Resolve the stale first promise
      resolveFirst!({ data: [event1] });
      await vi.runAllTimersAsync();
      await nextTick();

      // eventsLoading should still be true because the second (current) fetch is pending
      expect(get(result.eventsLoading)).toBe(true);

      // Resolve the second (current) promise
      resolveSecond!({ data: [event2] });
      await vi.runAllTimersAsync();
      await nextTick();

      expect(get(result.eventsLoading)).toBe(false);
    });

    it('should cancel stale events fetch when groupLoading becomes true', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      mockFetchHistoryEvents.mockResolvedValue({ data: [event1] });

      const groupLoading = ref<boolean>(false);
      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading,
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      useHistoryEventsData(options, emit);

      await waitForFetchEvents();
      mockCancelByTag.mockClear();

      // Simulate groups fetch starting (e.g. user changed page)
      set(groupLoading, true);
      await nextTick();

      expect(mockCancelByTag).toHaveBeenCalledWith('history-events-detail');
    });

    it('should not cancel events when groupLoading becomes false', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      mockFetchHistoryEvents.mockResolvedValue({ data: [event1] });

      const groupLoading = ref<boolean>(true);
      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading,
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      useHistoryEventsData(options, emit);

      await waitForFetchEvents();
      mockCancelByTag.mockClear();

      // groupLoading goes false (groups fetch completed)
      set(groupLoading, false);
      await nextTick();

      // cancelByTag should NOT be called when loading stops
      expect(mockCancelByTag).not.toHaveBeenCalled();
    });

    it('should clear events when groups become empty', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      mockFetchHistoryEvents.mockResolvedValueOnce({ data: [event1] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();
      expect(get(result.rawEvents)).toHaveLength(1);

      // Set groups to empty
      set(groups, createMockCollection([]));
      await waitForFetchEvents();

      expect(get(result.rawEvents)).toHaveLength(0);
    });
  });

  describe('swap event subgrouping', () => {
    async function waitForFetchEvents(): Promise<void> {
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
    }

    function createSwapEvent(overrides: Partial<Omit<HistoryEventEntry, 'entryType'>> = {}): HistoryEventEntry {
      const event: HistoryEventEntry = {
        amount: bigNumberify('100'),
        asset: 'ETH',
        entryType: HistoryEventEntryType.SWAP_EVENT,
        eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
        eventSubtype: 'spend',
        eventType: 'trade',
        extraData: null,
        groupIdentifier: 'group1',
        hidden: false,
        identifier: 1,
        ignoredInAccounting: false,
        location: 'kraken',
        locationLabel: 'Account 1',
        sequenceIndex: 0,
        states: [],
        timestamp: 1000000,
        ...overrides,
      };
      return event;
    }

    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should wrap multiple swap events in the same group into a subgroup array', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const swapSpend = createSwapEvent({ groupIdentifier: 'group1', identifier: 1, eventSubtype: 'spend' });
      const swapReceive = createSwapEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'receive', asset: 'USDC' });

      mockFetchHistoryEvents.mockResolvedValue({ data: [swapSpend, swapReceive] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([swapSpend]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const mapped = get(result.completeEventsMapped);
      // Should have one entry which is an array (subgroup) containing both swap events
      expect(mapped.group1).toHaveLength(1);
      expect(Array.isArray(mapped.group1[0])).toBe(true);
      expect((mapped.group1[0] as HistoryEventEntry[]).length).toBe(2);
    });

    it('should not wrap a single swap event into a subgroup', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const swapEvent = createSwapEvent({ groupIdentifier: 'group1', identifier: 1 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [swapEvent] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([swapEvent]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const mapped = get(result.completeEventsMapped);
      // Single swap event should not be wrapped
      expect(mapped.group1).toHaveLength(1);
      expect(Array.isArray(mapped.group1[0])).toBe(false);
    });

    it('should not wrap non-swap events into a subgroup', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });

      mockFetchHistoryEvents.mockResolvedValue({ data: [event1, event2] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([event1]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      const mapped = get(result.completeEventsMapped);
      // EVM events should remain as individual entries
      expect(mapped.group1).toHaveLength(2);
      expect(Array.isArray(mapped.group1[0])).toBe(false);
      expect(Array.isArray(mapped.group1[1])).toBe(false);
    });
  });

  describe('isSubgroupIncomplete', () => {
    async function waitForFetchEvents(): Promise<void> {
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
      await vi.runAllTimersAsync();
      await nextTick();
    }

    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return true when displayed subgroup has fewer events than complete', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const swapSpend = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });
      const swapReceive = createMockEvent({ asset: 'SPAM_TOKEN', groupIdentifier: 'group1', identifier: 2 });

      const swapSubgroup: HistoryEventRow = [swapSpend, swapReceive];
      mockFetchHistoryEvents.mockResolvedValue({ data: [swapSubgroup] });
      mockIsAssetIgnored.mockImplementation((asset: string) => asset === 'SPAM_TOKEN');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([swapSpend]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      // The displayed subgroup has 1 event (swapSpend), complete has 2
      const displayed = get(result.displayedEventsMapped);
      const displayedSubgroup = displayed.group1[0] as HistoryEventEntry[];
      expect(result.isSubgroupIncomplete(displayedSubgroup)).toBe(true);
    });

    it('should return false when displayed subgroup matches complete', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const swapSpend = createMockEvent({ asset: 'ETH', groupIdentifier: 'group1', identifier: 1 });
      const swapReceive = createMockEvent({ asset: 'USDC', groupIdentifier: 'group1', identifier: 2 });

      const swapSubgroup: HistoryEventRow = [swapSpend, swapReceive];
      mockFetchHistoryEvents.mockResolvedValue({ data: [swapSubgroup] });

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([swapSpend]));
      const options = {
        excludeIgnored: ref<boolean>(true),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      await waitForFetchEvents();

      // No ignored assets, so displayed matches complete
      const displayed = get(result.displayedEventsMapped);
      const displayedSubgroup = displayed.group1[0] as HistoryEventEntry[];
      expect(result.isSubgroupIncomplete(displayedSubgroup)).toBe(false);
    });

    it('should return false for empty events array', async () => {
      const { useHistoryEventsData } = await import('./use-history-events-data');

      const groups = ref<Collection<HistoryEventRow>>(createMockCollection([]));
      const options = {
        excludeIgnored: ref<boolean>(false),
        groupLoading: ref<boolean>(false),
        groups,
        pageParams: ref<HistoryEventRequestPayload | undefined>(undefined),
      };

      const emit = vi.fn();
      const result = useHistoryEventsData(options, emit);

      expect(result.isSubgroupIncomplete([])).toBe(false);
    });
  });
});
