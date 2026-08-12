import type { Ref, WritableComputedRef } from 'vue';
import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { ParamSource } from '@/modules/core/table/param-sources';
import { listParam, type PillParams, refParams, toPillParams } from '@/modules/core/table/param-refs';

/** The wire keys the manual balances table filters on, which the URL carries too. */
export const ManualBalanceFilterKeys = {
  ASSET: 'asset',
  LABEL: 'label',
  LOCATION: 'location',
} as const;

export type ManualBalanceFilterKey = typeof ManualBalanceFilterKeys[keyof typeof ManualBalanceFilterKeys];

export type Filters = MatchedKeyword<ManualBalanceFilterKey>;

/**
 * The tags key, which is not part of the filter bag above: tags ride a param, to the request and to
 * the url alike, which is what lets the bar absorb the standalone tag selector this table used to
 * carry.
 *
 * Declared once here so the request, the url and the bar's own bag come off one statement. The url
 * carries them comma-joined, which is what an array stringifies to.
 */
export function manualBalanceTagsParams(tags: Ref<string[]>): {
  source: ParamSource;
  pillParams: WritableComputedRef<PillParams>;
} {
  const spec = { tags: listParam(tags, { separator: ',' }) };

  return {
    pillParams: toPillParams(spec),
    source: refParams(spec, { to: 'both' }),
  };
}
