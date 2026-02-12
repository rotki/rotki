import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/types/history/events/schemas';
import { useCompleteEvents } from './use-complete-events';

function createMockEvent(overrides: Omit<Partial<HistoryEventEntry>, 'entryType'> = {}): HistoryEventEntry {
  const event: HistoryEventEntry = {
    address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
    amount: bigNumberify('1'),
    asset: 'ETH',
    counterparty: null,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: 'group1',
    hidden: false,
    identifier: 1,
    ignoredInAccounting: false,
    location: 'ethereum',
    locationLabel: null,
    sequenceIndex: 0,
    states: [],
    timestamp: 1000000,
    txRef: 'tx1',
  };
  return { ...event, ...overrides };
}

describe('useCompleteEvents', () => {
  describe('getGroupEvents', () => {
    it('should return flattened events for a group', () => {
      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [event1, event2],
      }));

      const { getGroupEvents } = useCompleteEvents(completeEventsMapped);

      expect(getGroupEvents('group1')).toEqual([event1, event2]);
    });

    it('should flatten subgroups into a single array', () => {
      const approve = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapIn = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapOut = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [approve, [swapIn, swapOut]],
      }));

      const { getGroupEvents } = useCompleteEvents(completeEventsMapped);

      expect(getGroupEvents('group1')).toEqual([approve, swapIn, swapOut]);
    });

    it('should return empty array for unknown group', () => {
      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { getGroupEvents } = useCompleteEvents(completeEventsMapped);

      expect(getGroupEvents('unknown')).toEqual([]);
    });
  });

  describe('getCompleteSubgroupEvents', () => {
    it('should return the complete subgroup matching the displayed events', () => {
      const swapIn = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapOut = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });
      const hiddenEvent = createMockEvent({ groupIdentifier: 'group1', identifier: 4, eventSubtype: 'receive' });

      // Complete subgroup has 3 events, but displayed only shows 2
      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swapIn, swapOut, hiddenEvent]],
      }));

      const { getCompleteSubgroupEvents } = useCompleteEvents(completeEventsMapped);

      // Displayed events only contain swapIn and swapOut
      const result = getCompleteSubgroupEvents([swapIn, swapOut]);

      // Should return the complete subgroup (including hiddenEvent)
      expect(result).toEqual([swapIn, swapOut, hiddenEvent]);
    });

    it('should not return events from other subgroups', () => {
      const swap1In = createMockEvent({ groupIdentifier: 'group1', identifier: 1, eventSubtype: 'spend' });
      const swap1Out = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'receive' });
      const swap2In = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'spend' });
      const swap2Out = createMockEvent({ groupIdentifier: 'group1', identifier: 4, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swap1In, swap1Out], [swap2In, swap2Out]],
      }));

      const { getCompleteSubgroupEvents } = useCompleteEvents(completeEventsMapped);

      // Should return only the first subgroup
      expect(getCompleteSubgroupEvents([swap1In, swap1Out])).toEqual([swap1In, swap1Out]);
      // Should return only the second subgroup
      expect(getCompleteSubgroupEvents([swap2In, swap2Out])).toEqual([swap2In, swap2Out]);
    });

    it('should not include standalone events from the same group', () => {
      const approve = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapIn = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapOut = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [approve, [swapIn, swapOut]],
      }));

      const { getCompleteSubgroupEvents } = useCompleteEvents(completeEventsMapped);

      const result = getCompleteSubgroupEvents([swapIn, swapOut]);

      // Should return only the swap subgroup, not the approve event
      expect(result).toEqual([swapIn, swapOut]);
      expect(result).not.toContainEqual(approve);
    });

    it('should fall back to displayed events when no matching subgroup found', () => {
      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { getCompleteSubgroupEvents } = useCompleteEvents(completeEventsMapped);

      const displayed = [createMockEvent({ identifier: 99 })];
      expect(getCompleteSubgroupEvents(displayed)).toBe(displayed);
    });

    it('should handle empty displayed events', () => {
      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({}));

      const { getCompleteSubgroupEvents } = useCompleteEvents(completeEventsMapped);

      const empty: HistoryEventEntry[] = [];
      expect(getCompleteSubgroupEvents(empty)).toBe(empty);
    });
  });

  describe('getCompleteEventsForItem', () => {
    it('should return the subgroup for a swap event', () => {
      const approve = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapIn = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapOut = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [approve, [swapIn, swapOut]],
      }));

      const { getCompleteEventsForItem } = useCompleteEvents(completeEventsMapped);

      // When asking for swapIn, should return only the swap subgroup
      expect(getCompleteEventsForItem('group1', swapIn)).toEqual([swapIn, swapOut]);
      // When asking for swapOut, should return the same swap subgroup
      expect(getCompleteEventsForItem('group1', swapOut)).toEqual([swapIn, swapOut]);
    });

    it('should return all group events for a standalone (non-subgroup) event', () => {
      const approve = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const swapIn = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'spend' });
      const swapOut = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [approve, [swapIn, swapOut]],
      }));

      const { getCompleteEventsForItem } = useCompleteEvents(completeEventsMapped);

      // When asking for the standalone approve event, should return all flattened group events
      expect(getCompleteEventsForItem('group1', approve)).toEqual([approve, swapIn, swapOut]);
    });

    it('should return the correct subgroup with multiple subgroups in a group', () => {
      const swap1In = createMockEvent({ groupIdentifier: 'group1', identifier: 1, eventSubtype: 'spend' });
      const swap1Out = createMockEvent({ groupIdentifier: 'group1', identifier: 2, eventSubtype: 'receive' });
      const swap2In = createMockEvent({ groupIdentifier: 'group1', identifier: 3, eventSubtype: 'spend' });
      const swap2Out = createMockEvent({ groupIdentifier: 'group1', identifier: 4, eventSubtype: 'receive' });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [[swap1In, swap1Out], [swap2In, swap2Out]],
      }));

      const { getCompleteEventsForItem } = useCompleteEvents(completeEventsMapped);

      // Each swap event should resolve to its own subgroup only
      expect(getCompleteEventsForItem('group1', swap1In)).toEqual([swap1In, swap1Out]);
      expect(getCompleteEventsForItem('group1', swap2In)).toEqual([swap2In, swap2Out]);
      expect(getCompleteEventsForItem('group1', swap2Out)).toEqual([swap2In, swap2Out]);
    });

    it('should return all group events when event is not found in any subgroup', () => {
      const event1 = createMockEvent({ groupIdentifier: 'group1', identifier: 1 });
      const event2 = createMockEvent({ groupIdentifier: 'group1', identifier: 2 });
      const unknownEvent = createMockEvent({ groupIdentifier: 'group1', identifier: 99 });

      const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => ({
        group1: [event1, event2],
      }));

      const { getCompleteEventsForItem } = useCompleteEvents(completeEventsMapped);

      // Unknown event not in any subgroup → falls back to all group events
      expect(getCompleteEventsForItem('group1', unknownEvent)).toEqual([event1, event2]);
    });
  });
});
