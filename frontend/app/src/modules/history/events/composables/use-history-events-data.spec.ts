import type { Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/types/history/events/schemas';

const mockItemsPerPage = ref<number>(10);

// Mock external dependencies
const mockFetchHistoryEvents = vi.fn();
const mockIsAssetIgnored = vi.fn();

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(() => ({
    fetchHistoryEvents: mockFetchHistoryEvents,
  })),
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
      customized: false,
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

      expect(get(result.allEventsMapped)).toEqual({});
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
    async function waitForAsyncComputed(result: { events: any }): Promise<void> {
      // Trigger lazy asyncComputed by accessing the value
      get(result.events);
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
      const result = useHistoryEventsData(options, emit);

      await waitForAsyncComputed(result);

      expect(mockFetchHistoryEvents).toHaveBeenCalledWith(
        expect.objectContaining({
          groupIdentifiers: ['group1', 'group2'],
          limit: -1,
          offset: 0,
        }),
      );
    });

    it('should map events by groupIdentifier in allEventsMapped', async () => {
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

      await waitForAsyncComputed(result);

      const mapped = get(result.allEventsMapped);
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

      await waitForAsyncComputed(result);

      const mapped = get(result.allEventsMapped);
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

      await waitForAsyncComputed(result);

      expect(get(result.displayedEventsMapped)).toEqual(get(result.allEventsMapped));
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

      await waitForAsyncComputed(result);

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

      await waitForAsyncComputed(result);

      const displayed = get(result.displayedEventsMapped);
      expect(displayed.group1).toBeUndefined();
    });
  });
});
