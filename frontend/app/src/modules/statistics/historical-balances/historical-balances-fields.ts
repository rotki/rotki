import type { Ref, WritableComputedRef } from 'vue';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueDisplay } from '@/modules/core/table/pill/core/types';
import { type AccountFieldOptions, toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { listParam, type PillParams, stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** The keys the historical balances bar carries. Not wire keys: the page filters what it has loaded. */
const HistoricalBalancesFilterKeys = {
  ACCOUNTS: 'accounts',
  LOCATIONS: 'locations',
  SEARCH: 'search',
} as const;

/** What the fields need from the Vue layer to be built. */
export interface HistoricalBalancesFieldOptions {
  /** The locations holding anything on the day, by their raw id (`kraken`, `arbitrum_one`). */
  readonly locations: () => string[];
  /** The accounts holding anything on the day, and how each reads. */
  readonly accounts: AccountFieldOptions & {
    /** A blockie for an address, the exchange's logo for an account held on one. */
    readonly resolveDisplay: (value: string) => ValueDisplay | undefined;
  };
}

/**
 * The pill-bar fields for the historical balances table: where a balance is held, which account
 * holds it, and a keyword over the asset.
 *
 * Every field is param-bound, because the page filters the balances it already holds rather than
 * asking the backend, the way the per-asset locations table does. Location and account are
 * multi-valued: a balance is kept when its location and its account are each among those picked.
 */
export function toHistoricalBalancesFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: HistoricalBalancesFieldOptions,
): FieldDef[] {
  return [
    decorateSharedField(
      toParamFieldDef({
        key: 'location',
        label: (): string => t('common.location'),
        multiple: true,
        paramKey: HistoricalBalancesFilterKeys.LOCATIONS,
        suggest: options.locations,
        to: 'both',
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ),
    {
      ...toAccountField(
        { label: (): string => t('common.account'), paramKey: HistoricalBalancesFilterKeys.ACCOUNTS, to: 'both' },
        options.accounts,
      ),
      resolveDisplay: options.accounts.resolveDisplay,
    },
    toParamFieldDef({
      freeText: true,
      hint: (): string => t('historical_balances.filter.search_hint'),
      key: 'search',
      label: (): string => t('common.actions.search'),
      multiple: false,
      paramKey: HistoricalBalancesFilterKeys.SEARCH,
      to: 'both',
    }),
  ];
}

/** The page's three filter refs as the bar's params bag. */
export function historicalBalancesParams(
  locations: Ref<string[]>,
  accounts: Ref<string[]>,
  search: Ref<string>,
): WritableComputedRef<PillParams> {
  return toPillParams({
    [HistoricalBalancesFilterKeys.ACCOUNTS]: listParam(accounts),
    [HistoricalBalancesFilterKeys.LOCATIONS]: listParam(locations),
    [HistoricalBalancesFilterKeys.SEARCH]: stringParam(search),
  });
}
