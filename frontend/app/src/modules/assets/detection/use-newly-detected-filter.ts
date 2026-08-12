import type { MatchedKeyword } from '@/modules/core/table/filtering';
import { isNewDetectedTokenKind, type NewDetectedTokenKind } from '@/modules/assets/detection/types';

/**
 * The key the newly detected assets table filters on. Not a wire key: these rows live in the local
 * database, and `getData` reads it off the payload to build its own query.
 */
export const NewlyDetectedFilterKeys = {
  TOKEN_KIND: 'tokenKind',
} as const;

export type NewlyDetectedFilterKey = typeof NewlyDetectedFilterKeys[keyof typeof NewlyDetectedFilterKeys];

export type Filters = MatchedKeyword<NewlyDetectedFilterKey>;

/**
 * The kind the table is currently narrowed to, or nothing when the pill is absent and every kind is
 * shown. The bag types every value as one-or-many; this field is single-valued.
 */
export function tokenKindOf(filters: Filters): NewDetectedTokenKind | undefined {
  const picked = filters[NewlyDetectedFilterKeys.TOKEN_KIND];
  const value = (Array.isArray(picked) ? picked[0] : picked)?.toString();
  return isNewDetectedTokenKind(value) ? value : undefined;
}
