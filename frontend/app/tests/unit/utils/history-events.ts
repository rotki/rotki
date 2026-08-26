import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import {
  type AssetMovementEvent,
  type EvmHistoryEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
  type OnlineHistoryEvent,
} from '@/modules/history/events/schemas';

/**
 * The fields every history event carries, so a factory only has to state what its own case needs.
 *
 * @remarks
 * These are plain objects rather than `createMock` proxies on purpose: consumers spread an entry
 * (`{ ...entry, ...meta }`), and a proxy's `ownKeys` come from its `vi.fn()` target, so every
 * override would be silently dropped by the spread.
 */
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

/** Creates an exchange deposit or withdrawal. */
export function createAssetMovementEvent(
  overrides: Partial<Omit<AssetMovementEvent, 'entryType'>> = {},
): HistoryEventEntry {
  return { ...commonFields, extraData: null, entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT, ...overrides };
}

/** Creates a plain history event, which is what an asset movement becomes once resolved as external. */
export function createOnlineHistoryEvent(
  overrides: Partial<Omit<OnlineHistoryEvent, 'entryType'>> = {},
): HistoryEventEntry {
  return { ...commonFields, entryType: HistoryEventEntryType.HISTORY_EVENT, ...overrides };
}

/** Creates a decoded on-chain event. */
export function createEvmEvent(
  overrides: Partial<Omit<EvmHistoryEvent, 'entryType'>> = {},
): HistoryEventEntry {
  return { ...commonFields, address: null, counterparty: null, extraData: null, txRef: 'tx1', entryType: HistoryEventEntryType.EVM_EVENT, ...overrides };
}
