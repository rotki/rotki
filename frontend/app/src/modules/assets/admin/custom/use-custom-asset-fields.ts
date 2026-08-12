import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toCustomAssetFields } from '@/modules/assets/admin/custom/custom-asset-fields';

/**
 * The pill-bar fields for the custom assets table. Built inside a computed so the labels track the
 * locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 *
 * @param types the custom asset types the user has created, which the type pill offers and
 * validates against.
 */
export function useCustomAssetFields(types: MaybeRefOrGetter<string[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<FieldDef[]>(() => toCustomAssetFields((): string[] => toValue(types), t));
}
