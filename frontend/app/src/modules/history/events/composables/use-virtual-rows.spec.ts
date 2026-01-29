import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/types/history/events/schemas';
import { ROW_HEIGHTS, useVirtualRows } from './use-virtual-rows';

describe('use-virtual-rows', () => {
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

  describe('flattenedRows', () => {
    it('should create group header row for each group', () => {
      const group1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const group2 = createMockEvent({ groupIdentifier: 'group2', identifier: 2 });

      const groups = computed<HistoryEventEntry[]>(() => [group1, group2]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [group1],
        group2: [group2],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const headerRows = rows.filter(r => r.type === 'group-header');

      expect(headerRows).toHaveLength(2);
      expect(headerRows[0].groupId).toBe('group1');
      expect(headerRows[1].groupId).toBe('group2');
    });

    it('should create event rows for events in a group', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [event1, event2],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const eventRows = rows.filter(r => r.type === 'event-row');

      expect(eventRows).toHaveLength(2);
      expect(eventRows[0].type).toBe('event-row');
      if (eventRows[0].type === 'event-row') {
        expect(eventRows[0].data.identifier).toBe(1);
      }
    });

    it('should create placeholder rows when events are not loaded', () => {
      const group = createMockEvent({
        groupIdentifier: 'group1',
        identifier: 1,
        groupedEventsNum: 3,
      });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [], // No events loaded yet
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const placeholderRows = rows.filter(r => r.type === 'event-placeholder');

      expect(placeholderRows).toHaveLength(3);
    });

    it('should limit placeholder rows to INITIAL_EVENTS_LIMIT', () => {
      const group = createMockEvent({
        groupIdentifier: 'group1',
        identifier: 1,
        groupedEventsNum: 20, // More than initial limit of 6
      });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const placeholderRows = rows.filter(r => r.type === 'event-placeholder');

      expect(placeholderRows).toHaveLength(6); // INITIAL_EVENTS_LIMIT
    });

    it('should create swap-row for array events (subgroups)', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]], // Array = swap subgroup
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const swapRows = rows.filter(r => r.type === 'swap-row');

      expect(swapRows).toHaveLength(1);
      if (swapRows[0].type === 'swap-row') {
        expect(swapRows[0].events).toHaveLength(2);
      }
    });

    it('should create load-more row when there are hidden events', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 10 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const loadMoreRows = rows.filter(r => r.type === 'load-more');

      expect(loadMoreRows).toHaveLength(1);
      if (loadMoreRows[0].type === 'load-more') {
        expect(loadMoreRows[0].hiddenCount).toBe(4); // 10 - 6 (initial limit)
        expect(loadMoreRows[0].totalCount).toBe(10);
      }
    });

    it('should not create load-more row when all events are visible', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 3 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const loadMoreRows = rows.filter(r => r.type === 'load-more');

      expect(loadMoreRows).toHaveLength(0);
    });
  });

  describe('loadMoreEvents', () => {
    it('should increase visible count for a group', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 15 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows, loadMoreEvents } = useVirtualRows(groups, eventsByGroup);

      // Initially 6 events visible
      let eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(6);

      // Load more
      loadMoreEvents('group1');
      await nextTick();

      // Now 12 events visible (6 + 6)
      eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(12);
    });

    it('should update load-more row hidden count after loading more', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 15 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows, loadMoreEvents } = useVirtualRows(groups, eventsByGroup);

      // Initially 9 hidden (15 - 6)
      let loadMoreRow = get(flattenedRows).find(r => r.type === 'load-more');
      expect(loadMoreRow?.type === 'load-more' && loadMoreRow.hiddenCount).toBe(9);

      // Load more
      loadMoreEvents('group1');
      await nextTick();

      // Now 3 hidden (15 - 12)
      loadMoreRow = get(flattenedRows).find(r => r.type === 'load-more');
      expect(loadMoreRow?.type === 'load-more' && loadMoreRow.hiddenCount).toBe(3);
    });
  });

  describe('toggleSwapExpanded', () => {
    it('should expand swap row into individual event rows', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup);

      // Initially collapsed - shows swap-row
      let swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      expect(swapRows).toHaveLength(1);

      // Get the swap key
      const swapKey = swapRows[0].type === 'swap-row' ? swapRows[0].swapKey : '';

      // Expand
      toggleSwapExpanded(swapKey);
      await nextTick();

      // Now expanded - shows swap-collapse header and individual event rows
      swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'swap-collapse');
      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');

      expect(swapRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(1);
      expect(eventRows).toHaveLength(2);
    });

    it('should collapse expanded swap back to swap-row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup);

      // Get swap key and expand
      const swapKey = 'group1-0';
      toggleSwapExpanded(swapKey);
      await nextTick();

      // Verify expanded
      expect(get(flattenedRows).filter(r => r.type === 'swap-collapse')).toHaveLength(1);

      // Collapse
      toggleSwapExpanded(swapKey);
      await nextTick();

      // Back to collapsed
      const swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'swap-collapse');

      expect(swapRows).toHaveLength(1);
      expect(collapseRows).toHaveLength(0);
    });
  });

  describe('getRowHeight', () => {
    it('should return correct height for group-header row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [group],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup);

      expect(getRowHeight(0)).toBe(ROW_HEIGHTS['group-header']);
    });

    it('should return correct height for event-row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [group],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup);

      // Index 0 is group-header, index 1 is event-row
      expect(getRowHeight(1)).toBe(ROW_HEIGHTS['event-row']);
    });

    it('should return correct height for swap-row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup);

      // Index 0 is group-header, index 1 is swap-row
      expect(getRowHeight(1)).toBe(ROW_HEIGHTS['swap-row']);
    });

    it('should return correct height for load-more row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 10 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows, getRowHeight } = useVirtualRows(groups, eventsByGroup);

      // Find load-more row index
      const rows = get(flattenedRows);
      const loadMoreIndex = rows.findIndex(r => r.type === 'load-more');

      expect(getRowHeight(loadMoreIndex)).toBe(ROW_HEIGHTS['load-more']);
    });

    it('should return default event-row height for out of bounds index', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [group],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup);

      expect(getRowHeight(999)).toBe(ROW_HEIGHTS['event-row']);
    });
  });

  describe('empty state', () => {
    it('should return empty array when no groups', () => {
      const groups = computed<HistoryEventEntry[]>(() => []);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      expect(get(flattenedRows)).toHaveLength(0);
    });

    it('should handle group with no events in eventsByGroup', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);

      // Should have group header only (no placeholders if groupedEventsNum is undefined)
      expect(rows).toHaveLength(1);
      expect(rows[0].type).toBe('group-header');
    });
  });

  describe('matched movement rows', () => {
    function createAssetMovementEvent(overrides: Omit<Partial<HistoryEventEntry>, 'entryType'> = {}): HistoryEventEntry {
      const event: HistoryEventEntry = {
        amount: bigNumberify('100'),
        asset: 'ETH',
        states: [],
        entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
        eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
        eventSubtype: 'deposit',
        eventType: 'transfer',
        extraData: null,
        groupIdentifier: 'group1',
        hidden: false,
        identifier: 1,
        ignoredInAccounting: false,
        location: 'kraken',
        locationLabel: 'Account 1',
        sequenceIndex: 0,
        timestamp: 1000000,
      };
      return { ...event, ...overrides };
    }

    it('should create matched-movement-row when array contains an asset movement event', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      // Real data: first event is EVM_EVENT (chain side), second is ASSET_MOVEMENT_EVENT (exchange side)
      const chainEvent = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'remove asset' });
      const exchangeEvent = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'deposit asset' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[chainEvent, exchangeEvent]], // Array containing one asset movement = matched movement
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup);

      const rows = get(flattenedRows);
      const movementRows = rows.filter(r => r.type === 'matched-movement-row');
      const swapRows = rows.filter(r => r.type === 'swap-row');

      expect(movementRows).toHaveLength(1);
      expect(swapRows).toHaveLength(0); // Should NOT be a swap row
      if (movementRows[0].type === 'matched-movement-row') {
        expect(movementRows[0].events).toHaveLength(2);
      }
    });

    it('should expand matched-movement-row into individual event rows', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup);

      // Initially collapsed - shows matched-movement-row
      let movementRows = get(flattenedRows).filter(r => r.type === 'matched-movement-row');
      expect(movementRows).toHaveLength(1);

      // Get the movement key
      const movementKey = movementRows[0].type === 'matched-movement-row' ? movementRows[0].movementKey : '';

      // Expand
      toggleMovementExpanded(movementKey);
      await nextTick();

      // Now expanded - shows matched-movement-collapse header and individual event rows
      movementRows = get(flattenedRows).filter(r => r.type === 'matched-movement-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'matched-movement-collapse');
      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');

      expect(movementRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(1);
      expect(eventRows).toHaveLength(2);
    });

    it('should collapse expanded matched movement back to matched-movement-row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup);

      // Get movement key and expand
      const movementKey = 'group1-0';
      toggleMovementExpanded(movementKey);
      await nextTick();

      // Verify expanded
      expect(get(flattenedRows).filter(r => r.type === 'matched-movement-collapse')).toHaveLength(1);

      // Collapse
      toggleMovementExpanded(movementKey);
      await nextTick();

      // Back to collapsed
      const movementRows = get(flattenedRows).filter(r => r.type === 'matched-movement-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'matched-movement-collapse');

      expect(movementRows).toHaveLength(1);
      expect(collapseRows).toHaveLength(0);
    });

    it('should return correct height for matched-movement-row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup);

      // Index 0 is group-header, index 1 is matched-movement-row
      expect(getRowHeight(1)).toBe(ROW_HEIGHTS['matched-movement-row']);
    });

    it('should return correct height for matched-movement-collapse row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, getRowHeight, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup);

      // Expand the movement
      toggleMovementExpanded('group1-0');
      await nextTick();

      // Find matched-movement-collapse row index
      const rows = get(flattenedRows);
      const collapseIndex = rows.findIndex(r => r.type === 'matched-movement-collapse');

      expect(getRowHeight(collapseIndex)).toBe(ROW_HEIGHTS['matched-movement-collapse']);
    });
  });
});
