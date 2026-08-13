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
 * The chain and strict-chain keys, which ride params rather than the filter bag above: one is a
 * boolean, which the bag has no form for, and both replaced controls that stood beside the bar.
 *
 * Declared once so the request, the url and the bar's own bag come off the same pair. They used to
 * be written to the url with nothing reading them back, so a shared link opened unfiltered.
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
