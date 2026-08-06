import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Matcher } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts-filter';
import { toInternalTxConflictFields } from '@/modules/core/table/filters/internal-tx-conflict-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * The pill-bar fields for the internal transaction conflicts table. Built inside a computed so the
 * labels track the locale: fields built once at setup keep the language they were created in until
 * the component remounts.
 */
export function useInternalTxConflictFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Chain and date resolution is the same for every table filtering on them, so it comes from one
  // place rather than being restated here.
  const shared = useSharedFieldResolvers();

  return computed<FieldDef[]>(() => toInternalTxConflictFields(toValue(matchers), shared, t));
}
