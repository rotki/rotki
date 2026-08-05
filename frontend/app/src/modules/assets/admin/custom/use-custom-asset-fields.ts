import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-custom-assets-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toCustomAssetFields } from '@/modules/core/table/filters/custom-asset-fields';

/**
 * The pill-bar fields for the custom assets table. Built inside a computed so the labels track the
 * locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useCustomAssetFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<FieldDef[]>(() => toCustomAssetFields(toValue(matchers), t));
}
