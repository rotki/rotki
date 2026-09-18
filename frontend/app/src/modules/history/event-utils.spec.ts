import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { getMatchedMovementIgnoreIds } from '@/modules/history/event-utils';
import {
  type AssetMovementEvent,
  type EvmHistoryEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
} from '@/modules/history/events/schemas';

/**
 * The seam: which legs of a matched subgroup unlinking should add to the ignore list. Only asset
 * movements count, since the unmatched pool is built from them alone, so an ignore written for
 * anything else would be a row nothing reads.
 */
function movement(overrides: Partial<AssetMovementEvent> = {}): HistoryEventEntry {
  const base = {
    amount: bigNumberify(1),
    asset: 'ETH',
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: 'spend',
    eventType: 'withdrawal',
    extraData: null,
    groupIdentifier: 'movement-1',
    identifier: 1,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    sequenceIndex: 0,
    timestamp: 1700000000000,
  } satisfies AssetMovementEvent;

  return {
    ...base,
    actualGroupIdentifier: 'joined-1',
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
    ...overrides,
  };
}

function chainEvent(identifier: number): HistoryEventEntry {
  const base = {
    address: null,
    amount: bigNumberify(1),
    asset: 'ETH',
    counterparty: null,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventSubtype: 'receive',
    eventType: 'receive',
    extraData: null,
    groupIdentifier: '0xdead',
    identifier,
    location: 'ethereum',
    locationLabel: null,
    sequenceIndex: 0,
    timestamp: 1700000000000,
    txRef: '0xdead',
  } satisfies EvmHistoryEvent;

  return {
    ...base,
    actualGroupIdentifier: 'joined-1',
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
  };
}

describe('getMatchedMovementIgnoreIds', () => {
  it('should ignore the movement leg but not its fee', () => {
    expect(getMatchedMovementIgnoreIds([
      movement({ eventSubtype: 'spend', identifier: 1 }),
      movement({ eventSubtype: 'fee', identifier: 2 }),
    ])).toStrictEqual([1]);
  });

  it('should ignore both sides of a movement to movement match', () => {
    expect(getMatchedMovementIgnoreIds([
      movement({ eventSubtype: 'spend', identifier: 1 }),
      movement({ eventSubtype: 'receive', identifier: 2, location: 'binance' }),
    ])).toStrictEqual([1, 2]);
  });

  it('should skip a matched chain event, which the unmatched pool never holds', () => {
    expect(getMatchedMovementIgnoreIds([
      movement({ identifier: 1 }),
      chainEvent(2),
    ])).toStrictEqual([1]);
  });

  it('should skip a leg that is not part of a joined group', () => {
    expect(getMatchedMovementIgnoreIds([
      { ...movement({ identifier: 1 }), actualGroupIdentifier: undefined },
    ])).toStrictEqual([]);
  });
});
