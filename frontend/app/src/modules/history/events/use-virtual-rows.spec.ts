import type { ComputedRef } from 'vue';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/modules/history/events/schemas';
import { ROW_HEIGHTS, useVirtualRows, type VirtualRow } from './use-virtual-rows';

/** Mirrors INITIAL_EVENTS_LIMIT in use-virtual-rows.ts. */
const PAGE_SIZE = 6;

/** Mirrors LOAD_MORE_INCREMENT, which is a separate constant that happens to match. */
const LOAD_MORE_INCREMENT = 6;

/** More legs than two pages, so a second load-more still leaves some hidden. */
const LEG_COUNT = 15;

/** Subgroup keys as the composable minted them — the specs must not encode the key format. */
function swapKeys(rows: ComputedRef<VirtualRow[]>): string[] {
  return get(rows).flatMap(row => (row.type === 'swap-row' ? [row.swapKey] : []));
}

function movementKeys(rows: ComputedRef<VirtualRow[]>): string[] {
  return get(rows).flatMap(row => (row.type === 'matched-movement-row' ? [row.movementKey] : []));
}

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

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

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

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const eventRows = rows.filter(r => r.type === 'event-row');

      expect(eventRows).toHaveLength(2);
      expect(eventRows[0].type).toBe('event-row');
      expect(eventRows[0]).toHaveProperty('data.identifier', 1);
    });

    it('should create placeholder rows when events are not loaded', () => {
      const group = createMockEvent({
        groupIdentifier: 'group1',
        identifier: 1,
        groupedEventsNum: 3,
      });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const placeholderRows = rows.filter(r => r.type === 'event-placeholder');

      expect(placeholderRows).toHaveLength(3);
    });

    it('should limit placeholder rows to INITIAL_EVENTS_LIMIT', () => {
      const group = createMockEvent({
        groupIdentifier: 'group1',
        identifier: 1,
        groupedEventsNum: PAGE_SIZE * 3,
      });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const placeholderRows = rows.filter(r => r.type === 'event-placeholder');

      expect(placeholderRows).toHaveLength(PAGE_SIZE);
    });

    it('should create swap-row for array events (subgroups)', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const swapRows = rows.filter(r => r.type === 'swap-row');

      expect(swapRows).toHaveLength(1);
      expect(swapRows[0].type).toBe('swap-row');
      expect(swapRows[0]).toHaveProperty('events.length', 2);
    });

    it('should create load-more row when there are hidden events', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const total = PAGE_SIZE + 4;
      const events = Array.from({ length: total }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const loadMoreRows = rows.filter(r => r.type === 'load-more');

      expect(loadMoreRows).toHaveLength(1);
      expect(loadMoreRows[0].type).toBe('load-more');
      expect(loadMoreRows[0]).toHaveProperty('hiddenCount', total - PAGE_SIZE);
      expect(loadMoreRows[0]).toHaveProperty('totalCount', total);
    });

    it('should not create load-more row when all events are visible', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: 3 }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const loadMoreRows = rows.filter(r => r.type === 'load-more');

      expect(loadMoreRows).toHaveLength(0);
    });
  });

  describe('loadMoreEvents', () => {
    it('should increase visible count for a group', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: LEG_COUNT }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows, loadMoreEvents } = useVirtualRows(groups, eventsByGroup, () => false);

      let eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(PAGE_SIZE);

      loadMoreEvents('group1');
      await nextTick();

      eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(PAGE_SIZE + LOAD_MORE_INCREMENT);
    });

    it('should update load-more row hidden count after loading more', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const events = Array.from({ length: LEG_COUNT }, (_, i) =>
        createMockEvent({ groupIdentifier: 'group1', identifier: i + 1 }));

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: events,
      }));

      const { flattenedRows, loadMoreEvents } = useVirtualRows(groups, eventsByGroup, () => false);

      let loadMoreRow = get(flattenedRows).find(r => r.type === 'load-more');
      expect(loadMoreRow?.type === 'load-more' && loadMoreRow.hiddenCount).toBe(LEG_COUNT - PAGE_SIZE);

      loadMoreEvents('group1');
      await nextTick();

      loadMoreRow = get(flattenedRows).find(r => r.type === 'load-more');
      expect(loadMoreRow?.type === 'load-more' && loadMoreRow.hiddenCount).toBe(LEG_COUNT - PAGE_SIZE - LOAD_MORE_INCREMENT);
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

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      let swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      expect(swapRows).toHaveLength(1);

      const swapKey = swapRows[0].type === 'swap-row' ? swapRows[0].swapKey : '';

      toggleSwapExpanded(swapKey);
      await nextTick();

      swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'swap-collapse');
      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');

      expect(swapRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(1);
      expect(eventRows).toHaveLength(2);
    });

    it('should flag the collapse row of a matched bridge subgroup as bridge', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const depositLeg = createMockEvent({ eventSubtype: 'bridge', eventType: 'deposit', groupIdentifier: 'group1', identifier: 2, location: 'arbitrum_one' });
      const withdrawalLeg = createMockEvent({ eventSubtype: 'bridge', eventType: 'withdrawal', groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[depositLeg, withdrawalLeg]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const swapRows = get(flattenedRows).filter(r => r.type === 'swap-row');
      expect(swapRows).toHaveLength(1);

      toggleSwapExpanded(swapRows[0].type === 'swap-row' ? swapRows[0].swapKey : '');
      await nextTick();

      const collapseRows = get(flattenedRows).filter(r => r.type === 'swap-collapse');
      expect(collapseRows).toHaveLength(1);
      expect(collapseRows[0]).toHaveProperty('bridge', true);

      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(2);
      expect(eventRows.every(r => r.type === 'event-row' && r.linkedLeg)).toBe(true);
    });

    it('should not flag the collapse row of a plain swap subgroup as bridge', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapSpend = createMockEvent({ eventSubtype: 'spend', groupIdentifier: 'group1', identifier: 2 });
      const swapReceive = createMockEvent({ eventSubtype: 'receive', groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapSpend, swapReceive]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const swapRow = get(flattenedRows).find(r => r.type === 'swap-row');
      toggleSwapExpanded(swapRow?.type === 'swap-row' ? swapRow.swapKey : '');
      await nextTick();

      const collapseRows = get(flattenedRows).filter(r => r.type === 'swap-collapse');
      expect(collapseRows).toHaveLength(1);
      expect(collapseRows[0]).toHaveProperty('bridge', false);

      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows.every(r => r.type === 'event-row' && !r.linkedLeg)).toBe(true);
    });

    it('should assign subgroup-relative index so the first expanded event has index 0', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapSpend = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapReceive = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapSpend, swapReceive]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      toggleSwapExpanded(swapKeys(flattenedRows)[0]);
      await nextTick();

      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(2);

      expect(eventRows[0].type === 'event-row' && eventRows[0].index).toBe(0);
      expect(eventRows[1].type === 'event-row' && eventRows[1].index).toBe(1);
    });

    it('should assign index 0 to first event of each subgroup when two swap subgroups are expanded', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swap1Spend = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swap1Receive = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });
      const swap2Spend = createMockEvent({ groupIdentifier: 'group1', identifier: 4, eventSubtype: 'spend' });
      const swap2Receive = createMockEvent({ groupIdentifier: 'group1', identifier: 5, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swap1Spend, swap1Receive], [swap2Spend, swap2Receive]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const [firstSwap, secondSwap] = swapKeys(flattenedRows);
      toggleSwapExpanded(firstSwap);
      toggleSwapExpanded(secondSwap);
      await nextTick();

      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(4);

      expect(eventRows[0].type === 'event-row' && eventRows[0].index).toBe(0);
      expect(eventRows[1].type === 'event-row' && eventRows[1].index).toBe(1);
      // Indexing restarts per subgroup rather than running across the group.
      expect(eventRows[2].type === 'event-row' && eventRows[2].index).toBe(0);
      expect(eventRows[3].type === 'event-row' && eventRows[3].index).toBe(1);

      expect(eventRows[0].type === 'event-row' && eventRows[0].data.identifier).toBe(2);
      expect(eventRows[2].type === 'event-row' && eventRows[2].data.identifier).toBe(4);
    });

    it('should force-expand swap and hide collapse header when subgroup is incomplete', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => true);

      const rows = get(flattenedRows);
      const swapRows = rows.filter(r => r.type === 'swap-row');
      const collapseRows = rows.filter(r => r.type === 'swap-collapse');
      const eventRows = rows.filter(r => r.type === 'event-row');

      // Should be expanded without collapse header
      expect(swapRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(0);
      expect(eventRows).toHaveLength(2);
      expect(eventRows[0].type === 'event-row' && eventRows[0].data.identifier).toBe(2);
      expect(eventRows[1].type === 'event-row' && eventRows[1].data.identifier).toBe(3);
    });

    it('should keep a swap expanded when an event above it is removed, shifting its index', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const leading = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const swapEventA = createMockEvent({ groupIdentifier: 'group1', identifier: 3 });
      const swapEventB = createMockEvent({ groupIdentifier: 'group1', identifier: 4 });

      const leadingPresent = ref<boolean>(true);
      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: get(leadingPresent)
          ? [leading, [swapEventA, swapEventB]]
          : [[swapEventA, swapEventB]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const swapRow = get(flattenedRows).find(r => r.type === 'swap-row');
      toggleSwapExpanded(swapRow?.type === 'swap-row' ? swapRow.swapKey : '');
      await nextTick();
      expect(get(flattenedRows).filter(r => r.type === 'swap-collapse')).toHaveLength(1);

      // The event above the swap goes away, so the swap moves from index 1 to index 0.
      set(leadingPresent, false);
      await nextTick();

      expect(get(flattenedRows).filter(r => r.type === 'swap-collapse')).toHaveLength(1);
      expect(get(flattenedRows).filter(r => r.type === 'swap-row')).toHaveLength(0);
    });

    it('should collapse expanded swap back to swap-row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapEvent1 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const swapEvent2 = createMockEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapEvent1, swapEvent2]],
      }));

      const { flattenedRows, toggleSwapExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const swapRow = get(flattenedRows).find(r => r.type === 'swap-row');
      const swapKey = swapRow?.type === 'swap-row' ? swapRow.swapKey : '';
      toggleSwapExpanded(swapKey);
      await nextTick();

      expect(get(flattenedRows).filter(r => r.type === 'swap-collapse')).toHaveLength(1);

      toggleSwapExpanded(swapKey);
      await nextTick();

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

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

      expect(getRowHeight(0)).toBe(ROW_HEIGHTS['group-header']);
    });

    it('should return correct height for event-row', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [group],
      }));

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

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

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

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

      const { flattenedRows, getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

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

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

      expect(getRowHeight(999)).toBe(ROW_HEIGHTS['event-row']);
    });
  });

  describe('empty state', () => {
    it('should return empty array when no groups', () => {
      const groups = computed<HistoryEventEntry[]>(() => []);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      expect(get(flattenedRows)).toHaveLength(0);
    });

    it('should handle group with no events in eventsByGroup', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

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
      const chainEvent = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'remove asset' });
      const exchangeEvent = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'deposit asset' });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[chainEvent, exchangeEvent]],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => false);

      const rows = get(flattenedRows);
      const movementRows = rows.filter(r => r.type === 'matched-movement-row');
      const swapRows = rows.filter(r => r.type === 'swap-row');

      expect(movementRows).toHaveLength(1);
      expect(swapRows).toHaveLength(0); // Should NOT be a swap row
      expect(movementRows[0].type).toBe('matched-movement-row');
      expect(movementRows[0]).toHaveProperty('events.length', 2);
    });

    it('should expand matched-movement-row into individual event rows', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      let movementRows = get(flattenedRows).filter(r => r.type === 'matched-movement-row');
      expect(movementRows).toHaveLength(1);

      const movementKey = movementRows[0].type === 'matched-movement-row' ? movementRows[0].movementKey : '';

      toggleMovementExpanded(movementKey);
      await nextTick();

      movementRows = get(flattenedRows).filter(r => r.type === 'matched-movement-row');
      const collapseRows = get(flattenedRows).filter(r => r.type === 'matched-movement-collapse');
      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');

      expect(movementRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(1);
      expect(eventRows).toHaveLength(2);
    });

    it('should index expanded movement events from 0, keeping their edit and delete actions visible', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      toggleMovementExpanded(movementKeys(flattenedRows)[0]);
      await nextTick();

      const eventRows = get(flattenedRows).filter(r => r.type === 'event-row');
      expect(eventRows).toHaveLength(2);

      expect(eventRows[0].type === 'event-row' && eventRows[0].index).toBe(0);
      expect(eventRows[1].type === 'event-row' && eventRows[1].index).toBe(1);
    });

    it('should collapse expanded matched movement back to matched-movement-row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      const movementKey = movementKeys(flattenedRows)[0];
      toggleMovementExpanded(movementKey);
      await nextTick();

      expect(get(flattenedRows).filter(r => r.type === 'matched-movement-collapse')).toHaveLength(1);

      toggleMovementExpanded(movementKey);
      await nextTick();

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

      const { getRowHeight } = useVirtualRows(groups, eventsByGroup, () => false);

      // Index 0 is group-header, index 1 is matched-movement-row
      expect(getRowHeight(1)).toBe(ROW_HEIGHTS['matched-movement-row']);
    });

    it('should force-expand matched-movement and hide collapse header when subgroup is incomplete', () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows } = useVirtualRows(groups, eventsByGroup, () => true);

      const rows = get(flattenedRows);
      const movementRows = rows.filter(r => r.type === 'matched-movement-row');
      const collapseRows = rows.filter(r => r.type === 'matched-movement-collapse');
      const eventRows = rows.filter(r => r.type === 'event-row');

      // Should be expanded without collapse header
      expect(movementRows).toHaveLength(0);
      expect(collapseRows).toHaveLength(0);
      expect(eventRows).toHaveLength(2);
      expect(eventRows[0].type === 'event-row' && eventRows[0].data.identifier).toBe(2);
      expect(eventRows[1].type === 'event-row' && eventRows[1].data.identifier).toBe(3);
    });

    it('should return correct height for matched-movement-collapse row', async () => {
      const group = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const movementEvent1 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 2 });
      const movementEvent2 = createAssetMovementEvent({ groupIdentifier: 'group1', identifier: 3 });

      const groups = computed<HistoryEventEntry[]>(() => [group]);
      const eventsByGroup = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[movementEvent1, movementEvent2]],
      }));

      const { flattenedRows, getRowHeight, toggleMovementExpanded } = useVirtualRows(groups, eventsByGroup, () => false);

      toggleMovementExpanded(movementKeys(flattenedRows)[0]);
      await nextTick();

      const rows = get(flattenedRows);
      const collapseIndex = rows.findIndex(r => r.type === 'matched-movement-collapse');

      expect(getRowHeight(collapseIndex)).toBe(ROW_HEIGHTS['matched-movement-collapse']);
    });
  });
});
