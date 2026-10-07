import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useDataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { toHistoricalBalancesFields } from '@/modules/statistics/historical-balances/historical-balances-fields';

/**
 * The pill-bar fields for the historical balances table. Built inside a computed so the labels
 * track the locale.
 *
 * @remarks
 * An account reads the way it does on every other history page: the account options resolve every
 * `(location, locationLabel)` pair of the user's history, which is the domain a balance's account
 * comes from. Only the accounts holding something on the day are offered, since any other one can
 * only empty the table.
 *
 * @param locations - the locations holding anything on the day
 * @param accounts - the accounts holding anything on the day
 */
export function useHistoricalBalancesFields(
  locations: MaybeRefOrGetter<string[]>,
  accounts: MaybeRefOrGetter<string[]>,
): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const accountOptions = useDataIssueAccountOptions();

  return computed<FieldDef[]>(() => toHistoricalBalancesFields(shared, t, {
    accounts: { ...accountOptions, suggest: (): string[] => toValue(accounts) },
    locations: (): string[] => toValue(locations),
  }));
}
