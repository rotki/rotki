import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/assets/prices/use-oracle-prices-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { getOracleSourceLabel } from '@/modules/assets/prices/oracle-source-labels';
import { toOraclePriceFields } from '@/modules/core/table/filters/oracle-price-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * The pill-bar fields for the oracle prices table. Built inside a computed so the labels track the
 * locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useOraclePriceFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Asset and date resolution is the same for every table filtering on them, so it comes from one
  // place rather than being restated here.
  const shared = useSharedFieldResolvers();

  return computed<FieldDef[]>(() => toOraclePriceFields(toValue(matchers), shared, t, getOracleSourceLabel));
}
