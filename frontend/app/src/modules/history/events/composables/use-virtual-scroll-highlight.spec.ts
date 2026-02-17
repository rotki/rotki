import type { TablePaginationData } from '@rotki/ui-library';
import type { Ref } from 'vue';
import type { VirtualRow } from './use-virtual-rows';
import type { HighlightType } from '@/composables/history/events/types';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/types/history/events/schemas';
import { useVirtualScrollHighlight } from './use-virtual-scroll-highlight';

const { scrollToSpy } = vi.hoisted(() => ({
  scrollToSpy: vi.fn(),
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  return {
    ...actual,
    useMediaQuery: (): Ref<boolean> => ref<boolean>(false),
    useVirtualList: (_list: Ref, _options: any): object => ({
      containerProps: ref<object>({}),
      list: ref<{ data: VirtualRow; index: number }[]>([]),
      wrapperProps: ref<object>({}),
      scrollTo: scrollToSpy,
    }),
  };
});

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

function createEventRow(event: HistoryEventEntry, index: number = 0): VirtualRow {
  return { type: 'event-row', groupId: event.groupIdentifier, data: event, index };
}

function createGroupHeaderRow(event: HistoryEventEntry): VirtualRow {
  return { type: 'group-header', groupId: event.groupIdentifier, data: event };
}

function createSwapRow(events: HistoryEventEntry[], index: number = 0): VirtualRow {
  return { type: 'swap-row', groupId: events[0].groupIdentifier, events, index, swapKey: `swap-${events[0].identifier}` };
}

function createMatchedMovementRow(events: HistoryEventEntry[], index: number = 0): VirtualRow {
  return { type: 'matched-movement-row', groupId: events[0].groupIdentifier, events, index, movementKey: `movement-${events[0].identifier}` };
}

interface SetupResult {
  composable: ReturnType<typeof useVirtualScrollHighlight>;
  flattenedRows: Ref<VirtualRow[]>;
  highlightedIdentifiers: Ref<string[] | undefined>;
  highlightTypes: Ref<Record<string, HighlightType> | undefined>;
  loading: Ref<boolean>;
  pagination: Ref<TablePaginationData>;
}

function setupComposable(overrides: {
  rows?: VirtualRow[];
  identifiers?: string[];
  types?: Record<string, HighlightType>;
  loading?: boolean;
  pagination?: TablePaginationData;
} = {}): SetupResult {
  const flattenedRows = ref<VirtualRow[]>(overrides.rows ?? []);
  const highlightedIdentifiers = ref<string[] | undefined>(overrides.identifiers);
  const highlightTypes = ref<Record<string, HighlightType> | undefined>(overrides.types);
  const loading = ref<boolean>(overrides.loading ?? false);
  const pagination = ref<TablePaginationData>(overrides.pagination ?? { page: 1, total: 0, limit: 10 });

  const composable = useVirtualScrollHighlight({
    flattenedRows: computed<VirtualRow[]>(() => get(flattenedRows)),
    getRowHeight: (): number => 48,
    getCardHeight: (): number => 140,
    highlightedIdentifiers: computed<string[] | undefined>(() => get(highlightedIdentifiers)),
    highlightTypes: computed<Record<string, HighlightType> | undefined>(() => get(highlightTypes)),
    loading,
    pagination,
  });

  return { composable, flattenedRows, highlightedIdentifiers, highlightTypes, loading, pagination };
}

async function triggerDebouncedWatch(): Promise<void> {
  await nextTick();
  vi.advanceTimersByTime(250);
  await nextTick();
  await nextTick();
}

describe('use-virtual-scroll-highlight', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    scrollToSpy.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('isHighlighted', () => {
    it('should return false when no identifiers are set', () => {
      const { composable: { isHighlighted } } = setupComposable();
      expect(isHighlighted(createMockEvent({ identifier: 1 }))).toBe(false);
    });

    it('should return false when identifiers list is empty', () => {
      const { composable: { isHighlighted } } = setupComposable({ identifiers: [] });
      expect(isHighlighted(createMockEvent({ identifier: 1 }))).toBe(false);
    });

    it('should return true when event identifier is in the list', () => {
      const { composable: { isHighlighted } } = setupComposable({ identifiers: ['1', '2'] });
      expect(isHighlighted(createMockEvent({ identifier: 1 }))).toBe(true);
    });

    it('should return false when event identifier is not in the list', () => {
      const { composable: { isHighlighted } } = setupComposable({ identifiers: ['2', '3'] });
      expect(isHighlighted(createMockEvent({ identifier: 1 }))).toBe(false);
    });
  });

  describe('getHighlightType', () => {
    it('should return undefined when no types are set', () => {
      const { composable: { getHighlightType } } = setupComposable();
      expect(getHighlightType(createMockEvent({ identifier: 1 }))).toBeUndefined();
    });

    it('should return the correct highlight type for an event', () => {
      const { composable: { getHighlightType } } = setupComposable({
        types: { 1: 'warning', 2: 'success' },
      });
      expect(getHighlightType(createMockEvent({ identifier: 1 }))).toBe('warning');
      expect(getHighlightType(createMockEvent({ identifier: 2 }))).toBe('success');
    });

    it('should return undefined for an event without a type', () => {
      const { composable: { getHighlightType } } = setupComposable({
        types: { 1: 'warning' },
      });
      expect(getHighlightType(createMockEvent({ identifier: 99 }))).toBeUndefined();
    });
  });

  describe('isSwapHighlighted', () => {
    it('should return false when no identifiers are set', () => {
      const { composable: { isSwapHighlighted } } = setupComposable();
      const events = [createMockEvent({ identifier: 1 }), createMockEvent({ identifier: 2 })];
      expect(isSwapHighlighted(events)).toBe(false);
    });

    it('should return true when any event in the group is highlighted', () => {
      const { composable: { isSwapHighlighted } } = setupComposable({ identifiers: ['2'] });
      const events = [createMockEvent({ identifier: 1 }), createMockEvent({ identifier: 2 })];
      expect(isSwapHighlighted(events)).toBe(true);
    });

    it('should return false when no events in the group are highlighted', () => {
      const { composable: { isSwapHighlighted } } = setupComposable({ identifiers: ['3'] });
      const events = [createMockEvent({ identifier: 1 }), createMockEvent({ identifier: 2 })];
      expect(isSwapHighlighted(events)).toBe(false);
    });
  });

  describe('getSwapHighlightType', () => {
    it('should return undefined when no types are set', () => {
      const { composable: { getSwapHighlightType } } = setupComposable();
      expect(getSwapHighlightType([createMockEvent({ identifier: 1 })])).toBeUndefined();
    });

    it('should return the first matched type in the group', () => {
      const { composable: { getSwapHighlightType } } = setupComposable({
        types: { 2: 'success', 3: 'warning' },
      });
      const events = [
        createMockEvent({ identifier: 1 }),
        createMockEvent({ identifier: 2 }),
        createMockEvent({ identifier: 3 }),
      ];
      expect(getSwapHighlightType(events)).toBe('success');
    });

    it('should return undefined when no events in the group have types', () => {
      const { composable: { getSwapHighlightType } } = setupComposable({
        types: { 99: 'warning' },
      });
      const events = [createMockEvent({ identifier: 1 }), createMockEvent({ identifier: 2 })];
      expect(getSwapHighlightType(events)).toBeUndefined();
    });
  });

  describe('return value', () => {
    it('should return all expected properties', () => {
      const { composable } = setupComposable();
      expect(composable).toHaveProperty('containerProps');
      expect(composable).toHaveProperty('virtualList');
      expect(composable).toHaveProperty('wrapperProps');
      expect(composable).toHaveProperty('isCardLayout');
      expect(composable).toHaveProperty('isHighlighted');
      expect(composable).toHaveProperty('getHighlightType');
      expect(composable).toHaveProperty('isSwapHighlighted');
      expect(composable).toHaveProperty('getSwapHighlightType');
    });
  });

  describe('findRowIndexForIdentifier via auto-scroll', () => {
    it('should find event-row by identifier and scroll to it', async () => {
      const event = createMockEvent({ identifier: 5 });
      const rows: VirtualRow[] = [
        createEventRow(createMockEvent({ identifier: 1 }), 0),
        createEventRow(createMockEvent({ identifier: 3 }), 1),
        createEventRow(event, 2),
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['5'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).toHaveBeenCalledWith(2);
    });

    it('should find group-header by identifier and scroll to it', async () => {
      const event = createMockEvent({ identifier: 10 });
      const rows: VirtualRow[] = [
        createGroupHeaderRow(createMockEvent({ identifier: 1 })),
        createGroupHeaderRow(event),
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['10'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).toHaveBeenCalledWith(1);
    });

    it('should find swap-row by event identifier and scroll to it', async () => {
      const events = [createMockEvent({ identifier: 10 }), createMockEvent({ identifier: 20 })];
      const rows: VirtualRow[] = [
        createEventRow(createMockEvent({ identifier: 1 }), 0),
        createSwapRow(events, 1),
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['20'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).toHaveBeenCalledWith(1);
    });

    it('should find matched-movement-row by event identifier and scroll to it', async () => {
      const events = [createMockEvent({ identifier: 30 }), createMockEvent({ identifier: 40 })];
      const rows: VirtualRow[] = [
        createEventRow(createMockEvent({ identifier: 1 }), 0),
        createMatchedMovementRow(events, 1),
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['40'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).toHaveBeenCalledWith(1);
    });

    it('should not scroll when identifier is not found in any row', async () => {
      const rows: VirtualRow[] = [
        createEventRow(createMockEvent({ identifier: 1 }), 0),
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['999'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should return -1 for non-matchable row types like load-more', async () => {
      const rows: VirtualRow[] = [
        { type: 'load-more', groupId: 'g1', hiddenCount: 3, totalCount: 10 },
      ];

      const { loading } = setupComposable({
        rows,
        identifiers: ['1'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });
  });

  describe('calculateScrollPosition via auto-scroll with two highlights', () => {
    it('should show both highlights when close together (distance <= 3)', async () => {
      const rows: VirtualRow[] = Array.from({ length: 10 }, (_, i) =>
        createEventRow(createMockEvent({ identifier: i + 1 }), i));

      const { loading } = setupComposable({
        rows,
        identifiers: ['3', '5'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).toHaveBeenCalledWith(2);
    });

    it('should position secondary at bottom when after primary (distance > 3)', async () => {
      const rows: VirtualRow[] = Array.from({ length: 20 }, (_, i) =>
        createEventRow(createMockEvent({ identifier: i + 1 }), i));

      const { loading } = setupComposable({
        rows,
        identifiers: ['2', '15'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      // non-card: secondaryIndex(14) - estimatedViewportRows(10) + bottomOffset(4) = 8
      expect(scrollToSpy).toHaveBeenCalledWith(8);
    });

    it('should position secondary at top when before primary (distance > 3)', async () => {
      const rows: VirtualRow[] = Array.from({ length: 20 }, (_, i) =>
        createEventRow(createMockEvent({ identifier: i + 1 }), i));

      const { loading } = setupComposable({
        rows,
        identifiers: ['15', '2'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      // secondary(1) is before primary(14), so secondaryIndex = 1
      expect(scrollToSpy).toHaveBeenCalledWith(1);
    });
  });

  describe('auto-scroll watcher guards', () => {
    it('should not scroll while loading', async () => {
      const rows: VirtualRow[] = [createEventRow(createMockEvent({ identifier: 1 }), 0)];

      setupComposable({
        rows,
        identifiers: ['1'],
        loading: true,
      });

      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should not scroll when identifiers are undefined', async () => {
      const rows: VirtualRow[] = [createEventRow(createMockEvent({ identifier: 1 }), 0)];

      const { loading } = setupComposable({
        rows,
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should not scroll when identifiers are empty', async () => {
      const rows: VirtualRow[] = [createEventRow(createMockEvent({ identifier: 1 }), 0)];

      const { loading } = setupComposable({
        rows,
        identifiers: [],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should not scroll when rows are empty', async () => {
      const { loading } = setupComposable({
        rows: [],
        identifiers: ['1'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should not scroll a second time without identifiers changing', async () => {
      const rows: VirtualRow[] = [createEventRow(createMockEvent({ identifier: 1 }), 0)];

      const { loading } = setupComposable({
        rows,
        identifiers: ['1'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();
      expect(scrollToSpy).toHaveBeenCalledTimes(1);

      scrollToSpy.mockClear();

      // Trigger the watcher again by toggling loading
      set(loading, true);
      await nextTick();
      set(loading, false);
      await triggerDebouncedWatch();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should allow re-scroll when identifiers change', async () => {
      const rows: VirtualRow[] = [
        createEventRow(createMockEvent({ identifier: 1 }), 0),
        createEventRow(createMockEvent({ identifier: 2 }), 1),
      ];

      const { loading, highlightedIdentifiers } = setupComposable({
        rows,
        identifiers: ['1'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();
      expect(scrollToSpy).toHaveBeenCalledWith(0);

      scrollToSpy.mockClear();

      set(highlightedIdentifiers, ['2']);
      await triggerDebouncedWatch();
      expect(scrollToSpy).toHaveBeenCalledWith(1);
    });
  });

  describe('auto-scroll with 3+ highlights', () => {
    it('should scroll to last highlight when not visible', async () => {
      const rows: VirtualRow[] = Array.from({ length: 10 }, (_, i) =>
        createEventRow(createMockEvent({ identifier: i + 1 }), i));

      const { loading } = setupComposable({
        rows,
        identifiers: ['1', '5', '9'],
        loading: true,
      });

      set(loading, false);
      await triggerDebouncedWatch();

      // virtualList mock returns empty list, so isRowVisible returns false → scrolls to last index (8)
      expect(scrollToSpy).toHaveBeenCalledWith(8);
    });
  });

  describe('pagination watcher', () => {
    it('should scroll to top when page changes', async () => {
      const { pagination } = setupComposable({
        pagination: { page: 1, total: 100, limit: 10 },
      });

      set(pagination, { page: 2, total: 100, limit: 10 });
      await nextTick();

      expect(scrollToSpy).toHaveBeenCalledWith(0);
    });

    it('should not scroll to top when page stays the same', async () => {
      const { pagination } = setupComposable({
        pagination: { page: 1, total: 100, limit: 10 },
      });

      set(pagination, { page: 1, total: 200, limit: 10 });
      await nextTick();

      expect(scrollToSpy).not.toHaveBeenCalled();
    });

    it('should not scroll to top when there is a pending highlight scroll', async () => {
      const rows: VirtualRow[] = [createEventRow(createMockEvent({ identifier: 1 }), 0)];

      const { pagination, highlightedIdentifiers } = setupComposable({
        rows,
        pagination: { page: 1, total: 100, limit: 10 },
      });

      // Setting identifiers triggers the watch(highlightedIdentifiers) → pendingHighlightScroll=true
      set(highlightedIdentifiers, ['1']);
      await nextTick();

      set(pagination, { page: 2, total: 100, limit: 10 });
      await nextTick();

      // scrollTo should not have been called with 0 (pagination scroll suppressed)
      expect(scrollToSpy).not.toHaveBeenCalledWith(0);
    });
  });
});
