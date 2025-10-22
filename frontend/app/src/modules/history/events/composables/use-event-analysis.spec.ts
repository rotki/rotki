import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry, type HistoryEventRow } from '@/types/history/events/schemas';
import { analyzeSelectedEvents } from './use-event-analysis';

describe('use-event-analysis', () => {
  describe('analyzeSelectedEvents', () => {
    let mockEvmEvent1: HistoryEventEntry;
    let mockEvmEvent2: HistoryEventEntry;
    let mockEvmEvent3: HistoryEventEntry;
    let mockSwapEvent1: HistoryEventEntry;
    let mockSwapEvent2: HistoryEventEntry;
    let mockEvmSwapEvent1: HistoryEventEntry;
    let mockEvmSwapEvent2: HistoryEventEntry;

    beforeEach(() => {
      mockEvmEvent1 = {
        address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        amount: bigNumberify('100'),
        asset: 'ETH',
        counterparty: null,
        customized: false,
        entryType: HistoryEventEntryType.EVM_EVENT,
        eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
        eventIdentifier: '0xabc123',
        eventSubtype: 'spend',
        eventType: 'transfer',
        extraData: null,
        identifier: 1,
        ignoredInAccounting: false,
        location: 'ethereum',
        locationLabel: 'Account 1',
        sequenceIndex: 0,
        timestamp: 1000000,
        txRef: 'tx1',
      };

      mockEvmEvent2 = {
        ...mockEvmEvent1,
        identifier: 2,
        sequenceIndex: 1,
      };

      mockEvmEvent3 = {
        ...mockEvmEvent1,
        eventIdentifier: '0xdef456',
        identifier: 3,
        txRef: 'tx2',
      };

      mockSwapEvent1 = {
        amount: bigNumberify('100'),
        asset: 'ETH',
        customized: false,
        entryType: HistoryEventEntryType.SWAP_EVENT,
        eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
        eventIdentifier: 'swap123',
        eventSubtype: 'spend',
        eventType: 'trade',
        extraData: null,
        identifier: 10,
        ignoredInAccounting: false,
        location: 'kraken',
        locationLabel: 'Account 1',
        sequenceIndex: 0,
        timestamp: 1000000,
      };

      mockSwapEvent2 = {
        ...mockSwapEvent1,
        eventSubtype: 'receive',
        identifier: 11,
        sequenceIndex: 1,
      };

      mockEvmSwapEvent1 = {
        address: '0x9531C059098e3d194fF87FebB587aB07B30B1306',
        amount: bigNumberify('200'),
        asset: 'USDC',
        counterparty: 'uniswap',
        customized: false,
        entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
        eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
        eventIdentifier: '0xswap789',
        eventSubtype: 'spend',
        eventType: 'trade',
        extraData: null,
        identifier: 20,
        ignoredInAccounting: false,
        location: 'ethereum',
        locationLabel: 'Account 2',
        sequenceIndex: 0,
        timestamp: 2000000,
        txRef: 'tx3',
      };

      mockEvmSwapEvent2 = {
        ...mockEvmSwapEvent1,
        eventSubtype: 'receive',
        identifier: 21,
        sequenceIndex: 1,
      };
    });

    it('should return empty results when no events are selected', () => {
      const result = analyzeSelectedEvents([], [], {});

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should identify complete EVM transaction when all events are selected', () => {
      const selectedIds = [1, 2];
      const originalGroups: HistoryEventRow[] = [mockEvmEvent1, mockEvmEvent2];
      const groupedEventsByTxRef = {
        '0xabc123': [mockEvmEvent1, mockEvmEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(1);
      expect(result.completeTransactions.get('tx1')).toEqual({
        chain: 'ethereum',
        eventIdentifier: '0xabc123',
        events: [1, 2],
      });
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should handle partial EVM transaction selection without swap events', () => {
      const selectedIds = [1];
      const originalGroups: HistoryEventRow[] = [mockEvmEvent1, mockEvmEvent2];
      const groupedEventsByTxRef = {
        '0xabc123': [mockEvmEvent1, mockEvmEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([1]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should detect partial swap group in array format', () => {
      const selectedIds = [10];
      const swapGroup = [mockSwapEvent1, mockSwapEvent2];
      const originalGroups: HistoryEventRow[] = [swapGroup];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([
        {
          groupIds: [10, 11],
          selectedIds: [10],
        },
      ]);
    });

    it('should allow complete swap group selection in array format', () => {
      const selectedIds = [10, 11];
      const swapGroup = [mockSwapEvent1, mockSwapEvent2];
      const originalGroups: HistoryEventRow[] = [swapGroup];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([10, 11]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should detect partial EVM swap events in transaction', () => {
      const selectedIds = [20];
      const originalGroups: HistoryEventRow[] = [mockEvmSwapEvent1, mockEvmSwapEvent2];
      const groupedEventsByTxRef = {
        '0xswap789': [mockEvmSwapEvent1, mockEvmSwapEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([
        {
          groupIds: [20, 21],
          selectedIds: [20],
        },
      ]);
    });

    it('should identify complete EVM swap transaction when all events are selected', () => {
      const selectedIds = [20, 21];
      const originalGroups: HistoryEventRow[] = [mockEvmSwapEvent1, mockEvmSwapEvent2];
      const groupedEventsByTxRef = {
        '0xswap789': [mockEvmSwapEvent1, mockEvmSwapEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      // EVM swap events are processed via processSingleSwapEvent (since isSwapTypeEvent matches first)
      // When all swap events are selected, they're NOT marked as processed and end up in partialEventIds
      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([20, 21]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should handle single swap event and find related swap events', () => {
      const selectedIds = [10];
      const originalGroups: HistoryEventRow[] = [mockSwapEvent1, mockSwapEvent2];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([
        {
          groupIds: [10, 11],
          selectedIds: [10],
        },
      ]);
    });

    it('should handle multiple complete transactions', () => {
      const selectedIds = [1, 2, 3];
      const originalGroups: HistoryEventRow[] = [mockEvmEvent1, mockEvmEvent2, mockEvmEvent3];
      const groupedEventsByTxRef = {
        '0xabc123': [mockEvmEvent1, mockEvmEvent2],
        '0xdef456': [mockEvmEvent3],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(2);
      expect(result.completeTransactions.get('tx1')).toEqual({
        chain: 'ethereum',
        eventIdentifier: '0xabc123',
        events: [1, 2],
      });
      expect(result.completeTransactions.get('tx2')).toEqual({
        chain: 'ethereum',
        eventIdentifier: '0xdef456',
        events: [3],
      });
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should handle mixed selection of complete transactions and partial swaps', () => {
      const selectedIds = [1, 2, 20];
      const originalGroups: HistoryEventRow[] = [
        mockEvmEvent1,
        mockEvmEvent2,
        mockEvmSwapEvent1,
        mockEvmSwapEvent2,
      ];
      const groupedEventsByTxRef = {
        '0xabc123': [mockEvmEvent1, mockEvmEvent2],
        '0xswap789': [mockEvmSwapEvent1, mockEvmSwapEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(1);
      expect(result.completeTransactions.get('tx1')).toEqual({
        chain: 'ethereum',
        eventIdentifier: '0xabc123',
        events: [1, 2],
      });
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([
        {
          groupIds: [20, 21],
          selectedIds: [20],
        },
      ]);
    });

    it('should handle non-swap array groups', () => {
      const mockGroupedEvent1: HistoryEventEntry = {
        ...mockEvmEvent1,
        identifier: 30,
      };
      const mockGroupedEvent2: HistoryEventEntry = {
        ...mockEvmEvent1,
        identifier: 31,
      };
      const selectedIds = [30, 31];
      const nonSwapGroup = [mockGroupedEvent1, mockGroupedEvent2];
      const originalGroups: HistoryEventRow[] = [nonSwapGroup];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      // Non-swap array groups mark selected events as processed
      // Since both are selected and processed, partialEventIds should be empty
      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should not duplicate processing of already processed events', () => {
      const selectedIds = [10, 11];
      const swapGroup = [mockSwapEvent1, mockSwapEvent2];
      const originalGroups: HistoryEventRow[] = [swapGroup, mockSwapEvent1, mockSwapEvent2];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      // The swapGroup array processes first - since all events are selected, they're not marked as processed
      // Then each individual swap event is processed via processSingleSwapEvent
      // Since all are selected and not processed, they end up in partialEventIds
      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([10, 11]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should handle empty groupedEventsByTxRef for EVM events', () => {
      const selectedIds = [1];
      const originalGroups: HistoryEventRow[] = [mockEvmEvent1];
      const groupedEventsByTxRef = {};

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      expect(result.completeTransactions.size).toBe(0);
      expect(result.partialEventIds).toEqual([1]);
      expect(result.partialSwapGroups).toEqual([]);
    });

    it('should handle complex scenario with multiple transaction types', () => {
      const selectedIds = [1, 2, 10, 20, 21];
      const swapGroup = [mockSwapEvent1, mockSwapEvent2];
      const originalGroups: HistoryEventRow[] = [
        mockEvmEvent1,
        mockEvmEvent2,
        swapGroup,
        mockEvmSwapEvent1,
        mockEvmSwapEvent2,
      ];
      const groupedEventsByTxRef = {
        '0xabc123': [mockEvmEvent1, mockEvmEvent2],
        '0xswap789': [mockEvmSwapEvent1, mockEvmSwapEvent2],
      };

      const result = analyzeSelectedEvents(selectedIds, originalGroups, groupedEventsByTxRef);

      // EVM events (1,2) are processed as complete transaction
      // Swap group with partial selection (only 10 selected) creates partial swap group
      // EVM swap events (20,21) are not processed and go to partialEventIds
      expect(result.completeTransactions.size).toBe(1);
      expect(result.completeTransactions.get('tx1')).toBeDefined();
      expect(result.partialEventIds).toEqual([20, 21]);
      expect(result.partialSwapGroups).toEqual([
        {
          groupIds: [10, 11],
          selectedIds: [10],
        },
      ]);
    });
  });
});
