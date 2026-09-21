import type { MatchedKeyword } from '@/modules/core/table/filtering';

/**
 * The keys the cex mapping table filters on, which the URL carries too. The API client sends them
 * as the backend's `connector` and `connector_symbol`.
 */
export const CexMappingFilterKeys = {
  LOCATION: 'location',
  LOCATION_SYMBOL: 'locationSymbol',
} as const;

type CexMappingFilterKey = typeof CexMappingFilterKeys[keyof typeof CexMappingFilterKeys];

export type Filters = MatchedKeyword<CexMappingFilterKey>;
