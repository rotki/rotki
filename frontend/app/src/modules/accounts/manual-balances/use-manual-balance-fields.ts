import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { Matcher } from '@/modules/core/table/filters/use-manual-balances-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toManualBalanceFields } from '@/modules/core/table/filters/manual-balance-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useTagFieldOptions } from '@/modules/core/table/filters/shared/use-tag-field-options';

/**
 * The pill-bar fields for the manual balances table. Built inside a computed so the labels track
 * the locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useManualBalanceFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Asset and location resolution is the same for every table filtering on them, so it comes from
  // one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const tagOptions = useTagFieldOptions();

  return computed<FieldDef[]>(() => toManualBalanceFields(
    toValue(matchers),
    shared,
    t,
    (): TagFieldOption[] => get(tagOptions),
  ));
}
