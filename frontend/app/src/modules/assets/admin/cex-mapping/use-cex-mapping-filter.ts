import type { MatchedKeyword } from '@/modules/core/table/filtering';

/** The wire keys the cex mapping table filters on, which the URL carries too. */
export const CexMappingFilterKeys = {
  LOCATION: 'location',
  LOCATION_SYMBOL: 'locationSymbol',
} as const;

export type CexMappingFilterKey = typeof CexMappingFilterKeys[keyof typeof CexMappingFilterKeys];

export type Filters = MatchedKeyword<CexMappingFilterKey>;
