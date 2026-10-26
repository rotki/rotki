import type { MatchedKeyword } from '@/modules/core/table/filtering';

/**
 * The keys the missing mappings table filters on. Not wire keys: this table's rows live in the
 * local database, and `getData` reads these off the payload to build its own predicate.
 */
export const MissingMappingsFilterKeys = {
  IDENTIFIER: 'identifier',
  LOCATION: 'location',
} as const;

type MissingMappingsFilterKey =
  typeof MissingMappingsFilterKeys[keyof typeof MissingMappingsFilterKeys];

export type Filters = MatchedKeyword<MissingMappingsFilterKey>;
