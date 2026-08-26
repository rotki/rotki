import type { Account, Blockchain, HistoryEventEntryType } from '@rotki/common';
import type { MaybeRefOrGetter } from 'vue';

type HistoryEventsPeriod =
  | { fromTimestamp?: string; toTimestamp?: string }
  | { fromTimestamp?: number; toTimestamp?: number };

/**
 * What a view has already decided for the user, stated once.
 *
 * Every consumer reads the same bag: the pill bar drops a field the view has pinned, the request
 * sources fold it into the payload, and the events fetch narrows to the chains it names. One bag
 * rather than sibling props, so a new restriction cannot reach only some of the three layers.
 *
 * An absent key means unrestricted, and an empty array reads the same — restricting to nothing is
 * not expressible. `externalAccounts` is the one exception, for the reason given on it.
 */
export interface HistoryEventsRestrictions {
  entryTypes?: HistoryEventEntryType[];
  eventTypes?: string[];
  /**
   * Accounts the view selects for the user, replacing the bar's account pill.
   *
   * Presence is the switch, so an empty array is meaningful here and not the same as omitting the
   * key: Kraken owns the account axis without pinning any address, and reads as `[]`. This was two
   * props, a boolean beside the list, which made "pinned to these accounts but the pill is still
   * offered" and "pill suppressed but the list is ignored" both expressible and neither meaningful.
   */
  externalAccounts?: Account[];
  location?: string;
  onlyChains?: Blockchain[];
  period?: HistoryEventsPeriod;
  protocols?: string[];
  validators?: number[];
}

interface RestrictionGetters {
  entryTypes: () => HistoryEventEntryType[] | undefined;
  eventTypes: () => string[];
  externalAccounts: () => Account[] | undefined;
  location: () => string | undefined;
  onlyChains: () => Blockchain[];
  period: () => HistoryEventsPeriod | undefined;
  protocols: () => string[];
  validators: () => number[] | undefined;
}

/**
 * Splits the bag into the per-axis getters the composables below it read.
 *
 * The list-valued axes default to `[]` here, in one place, because the consumers test them with
 * `.length` and treat absent and empty alike. The nullable ones stay nullable: `entryTypes`
 * distinguishes "every type" from a chosen set, `validators`/`location` gate a pill on presence
 * rather than on emptiness, and `externalAccounts` must not be defaulted at all — `[]` is a
 * meaningful value there and `undefined` is the off state.
 */
export function toRestrictionGetters(
  restrictions: MaybeRefOrGetter<HistoryEventsRestrictions>,
): RestrictionGetters {
  return {
    entryTypes: (): HistoryEventEntryType[] | undefined => toValue(restrictions).entryTypes,
    eventTypes: (): string[] => toValue(restrictions).eventTypes ?? [],
    externalAccounts: (): Account[] | undefined => toValue(restrictions).externalAccounts,
    location: (): string | undefined => toValue(restrictions).location,
    onlyChains: (): Blockchain[] => toValue(restrictions).onlyChains ?? [],
    period: (): HistoryEventsPeriod | undefined => toValue(restrictions).period,
    protocols: (): string[] => toValue(restrictions).protocols ?? [],
    validators: (): number[] | undefined => toValue(restrictions).validators,
  };
}
