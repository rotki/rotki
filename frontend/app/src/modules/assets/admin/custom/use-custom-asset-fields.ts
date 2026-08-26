import type { MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toCustomAssetFields } from '@/modules/assets/admin/custom/custom-asset-fields';

/**
 * The pill-bar fields for the custom assets table.
 *
 * @param types - the custom asset types the user has created, which the type pill offers and
 * validates against.
 */
export function useCustomAssetFields(types: MaybeRefOrGetter<string[]>): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });

  return toCustomAssetFields((): string[] => toValue(types), t);
}
