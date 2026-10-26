import type { Ref, WritableComputedRef } from 'vue';
import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { ParamSource } from '@/modules/core/table/param-sources';
import { boolParam, optionalStringParam, type PillParams, refParams, toPillParams } from '@/modules/core/table/param-refs';

export const AddressBookFilterKeys = {
  ADDRESS: 'address',
  NAME: 'nameSubstring',
} as const;

type AddressBookFilterKey = typeof AddressBookFilterKeys[keyof typeof AddressBookFilterKeys];

export type Filters = MatchedKeyword<AddressBookFilterKey>;

/**
 * The chain and strict-chain keys, which ride params rather than the filter bag above, because one
 * is a boolean and the bag has no form for that.
 *
 * Declared once so the request, the url and the bar's own bag all come off the same pair. Writing
 * to the url without reading back is what opens a shared link unfiltered.
 */
export function addressBookChainParams(
  chain: Ref<string | undefined>,
  strict: Ref<boolean>,
): { source: ParamSource; pillParams: WritableComputedRef<PillParams> } {
  const spec = {
    blockchain: optionalStringParam(chain),
    strictBlockchain: boolParam(strict),
  };

  return {
    pillParams: toPillParams(spec),
    source: refParams(spec, { to: 'both' }),
  };
}
