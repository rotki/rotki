import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import { HistoryEventEntryType } from '@rotki/common';

export const HYPE_IDENTIFIER = 'HYPE';

export const HYPERLIQUID_LOCATION = 'hyperliquid';

/**
 * The events of the Hyperliquid core staking account.
 *
 * @remarks
 * Core events are plain history events of the hyperliquid location and carry no counterparty,
 * so the entry type is what keeps out the HyperEVM ones, which are EVM events. Delegations are
 * informational events, and staking is the only thing core produces as informational.
 */
export const HYPERLIQUID_STAKING_RESTRICTIONS: HistoryEventsRestrictions = {
  entryTypes: [HistoryEventEntryType.HISTORY_EVENT],
  eventTypes: ['staking', 'informational'],
  location: HYPERLIQUID_LOCATION,
};
