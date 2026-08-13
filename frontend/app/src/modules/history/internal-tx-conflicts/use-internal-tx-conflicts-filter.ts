import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';

/** The wire keys the internal transaction conflicts table filters on. */
export const InternalTxConflictFilterKeys = {
  CHAIN: 'chain',
  FROM_TIMESTAMP: 'fromTimestamp',
  TO_TIMESTAMP: 'toTimestamp',
} as const;

type InternalTxConflictFilterKey = typeof InternalTxConflictFilterKeys[keyof typeof InternalTxConflictFilterKeys];

export type Filters = MatchedKeywordWithBehaviour<InternalTxConflictFilterKey>;
