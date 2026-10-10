import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import { Blockchain, HistoryEventEntryType } from '@rotki/common';

export const SOL_IDENTIFIER = 'SOL';

const CPT_SOLANA_STAKE = 'solana-stake';

/**
 * The events of the native Solana stake program.
 *
 * @remarks
 * Filtered by counterparty and not by the staking event type, because delegating, deactivating,
 * splitting and merging stake accounts are informational events of the same counterparty.
 */
export const SOLANA_STAKING_RESTRICTIONS: HistoryEventsRestrictions = {
  entryTypes: [HistoryEventEntryType.SOLANA_EVENT],
  onlyChains: [Blockchain.SOLANA],
  protocols: [CPT_SOLANA_STAKE],
};
