import type { MatchedKeyword } from '@/modules/core/table/filtering';

/** The wire keys the data issues table filters on, which the URL carries too. */
export const DataIssuesFilterKeys = {
  ACCOUNT: 'locationLabel',
  ASSET: 'asset',
  END: 'toTimestamp',
  KIND: 'kind',
  START: 'fromTimestamp',
  STATE: 'state',
} as const;

type DataIssuesFilterKey = typeof DataIssuesFilterKeys[keyof typeof DataIssuesFilterKeys];

export type Filters = MatchedKeyword<DataIssuesFilterKey>;
