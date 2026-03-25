import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  type AssetMovementEvent,
  type EvmHistoryEvent,
  type EvmSwapEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
  type OnlineHistoryEvent,
  type SolanaSwapEvent,
  type SwapEvent,
} from '@/types/history/events/schemas';
import { hideDeleteAction, hideEditAction, shouldDeleteGroup } from './event-action-visibility';

const commonFields = {
  amount: bigNumberify('1'),
  asset: 'ETH',
  eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
  eventSubtype: 'spend',
  eventType: 'trade',
  groupIdentifier: 'group1',
  hidden: false,
  identifier: 1,
  ignoredInAccounting: false,
  location: 'ethereum',
  locationLabel: null,
  sequenceIndex: 0,
  states: [],
  timestamp: 1000000,
};

function createEvmEvent(overrides: Partial<Omit<EvmHistoryEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, address: null, counterparty: null, extraData: null, txRef: 'tx1', entryType: HistoryEventEntryType.EVM_EVENT, ...overrides };
}

function createEvmSwapEvent(overrides: Partial<Omit<EvmSwapEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, address: null, counterparty: null, extraData: null, txRef: 'tx1', entryType: HistoryEventEntryType.EVM_SWAP_EVENT, ...overrides };
}

function createSolanaSwapEvent(overrides: Partial<Omit<SolanaSwapEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, address: null, counterparty: null, extraData: null, txRef: 'tx1', entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT, ...overrides };
}

function createSwapEvent(overrides: Partial<Omit<SwapEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, extraData: null, entryType: HistoryEventEntryType.SWAP_EVENT, ...overrides };
}

function createAssetMovementEvent(overrides: Partial<Omit<AssetMovementEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, extraData: null, entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT, ...overrides };
}

function createHistoryEvent(overrides: Partial<Omit<OnlineHistoryEvent, 'entryType'>> = {}): HistoryEventEntry {
  return { ...commonFields, entryType: HistoryEventEntryType.HISTORY_EVENT, ...overrides };
}

describe('eventActionVisibility', () => {
  describe('hideEditAction', () => {
    it('should show edit for swap primary event (index 0)', () => {
      const item = createEvmSwapEvent();
      expect(hideEditAction(item, 0)).toBe(false);
    });

    it('should hide edit for swap sub-events (index > 0)', () => {
      const item = createEvmSwapEvent();
      expect(hideEditAction(item, 1)).toBe(true);
      expect(hideEditAction(item, 2)).toBe(true);
    });

    it('should hide edit for solana swap sub-events', () => {
      const item = createSolanaSwapEvent();
      expect(hideEditAction(item, 1)).toBe(true);
    });

    it('should hide edit for online swap sub-events', () => {
      const item = createSwapEvent();
      expect(hideEditAction(item, 1)).toBe(true);
    });

    it('should hide edit for asset movement fee events', () => {
      const item = createAssetMovementEvent({ eventSubtype: 'fee' });
      expect(hideEditAction(item, 0)).toBe(true);
    });

    it('should show edit for regular events', () => {
      const item = createEvmEvent();
      expect(hideEditAction(item, 0)).toBe(false);
    });
  });

  describe('hideDeleteAction', () => {
    it('should hide delete for asset movement fee events', () => {
      const item = createAssetMovementEvent({ eventSubtype: 'fee' });
      expect(hideDeleteAction(item, 0, [])).toBe(true);
    });

    it('should show delete for swap fee sub-events', () => {
      const item = createEvmSwapEvent({ eventSubtype: 'fee' });
      expect(hideDeleteAction(item, 1, [])).toBe(false);
    });

    it('should hide delete for swap spend sub-event when only one spend exists', () => {
      const spend = createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const receive = createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 });
      expect(hideDeleteAction(spend, 1, [spend, receive])).toBe(true);
    });

    it('should show delete for swap spend sub-event when multiple spends exist', () => {
      const spend1 = createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const spend2 = createEvmSwapEvent({ eventSubtype: 'spend', identifier: 2 });
      const receive = createEvmSwapEvent({ eventSubtype: 'receive', identifier: 3 });
      expect(hideDeleteAction(spend2, 2, [spend1, spend2, receive])).toBe(false);
    });

    it('should hide delete for swap receive sub-event when only one receive exists', () => {
      const spend = createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const receive = createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 });
      expect(hideDeleteAction(receive, 1, [spend, receive])).toBe(true);
    });

    it('should show delete for swap receive sub-event when multiple receives exist', () => {
      const spend = createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const receive1 = createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 });
      const receive2 = createEvmSwapEvent({ eventSubtype: 'receive', identifier: 3 });
      expect(hideDeleteAction(receive2, 2, [spend, receive1, receive2])).toBe(false);
    });

    it('should not hide delete for swap primary event (index 0)', () => {
      const item = createEvmSwapEvent({ eventSubtype: 'spend' });
      expect(hideDeleteAction(item, 0, [item])).toBe(false);
    });

    it('should not hide delete for regular events', () => {
      const item = createEvmEvent();
      expect(hideDeleteAction(item, 0, [item])).toBe(false);
    });

    it('should work with solana swap events', () => {
      const spend = createSolanaSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const receive = createSolanaSwapEvent({ eventSubtype: 'receive', identifier: 2 });
      expect(hideDeleteAction(spend, 1, [spend, receive])).toBe(true);
    });

    it('should work with online swap events', () => {
      const spend1 = createSwapEvent({ eventSubtype: 'spend', identifier: 1 });
      const spend2 = createSwapEvent({ eventSubtype: 'spend', identifier: 2 });
      const receive = createSwapEvent({ eventSubtype: 'receive', identifier: 3 });
      expect(hideDeleteAction(spend2, 2, [spend1, spend2, receive])).toBe(false);
    });
  });

  describe('shouldDeleteGroup', () => {
    it('should delete group for asset movement events', () => {
      const item = createAssetMovementEvent({ eventSubtype: 'deposit' });
      expect(shouldDeleteGroup(item, 0)).toBe(true);
    });

    it('should delete group for online swap events at index 0', () => {
      const item = createSwapEvent();
      expect(shouldDeleteGroup(item, 0)).toBe(true);
    });

    it('should not delete group for online swap sub-events (index > 0)', () => {
      const item = createSwapEvent();
      expect(shouldDeleteGroup(item, 1)).toBe(false);
      expect(shouldDeleteGroup(item, 2)).toBe(false);
    });

    it('should delete group for evm swap at index 0', () => {
      const item = createEvmSwapEvent();
      expect(shouldDeleteGroup(item, 0)).toBe(true);
    });

    it('should not delete group for evm swap sub-events (index > 0)', () => {
      const item = createEvmSwapEvent();
      expect(shouldDeleteGroup(item, 1)).toBe(false);
      expect(shouldDeleteGroup(item, 2)).toBe(false);
    });

    it('should delete group for solana swap at index 0', () => {
      const item = createSolanaSwapEvent();
      expect(shouldDeleteGroup(item, 0)).toBe(true);
    });

    it('should not delete group for solana swap sub-events', () => {
      const item = createSolanaSwapEvent();
      expect(shouldDeleteGroup(item, 1)).toBe(false);
    });

    it('should not delete group for regular events', () => {
      const item = createEvmEvent();
      expect(shouldDeleteGroup(item, 0)).toBe(false);
    });

    it('should not delete group for history events', () => {
      const item = createHistoryEvent();
      expect(shouldDeleteGroup(item, 0)).toBe(false);
    });
  });
});
