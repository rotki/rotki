import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AssetLocation } from '@/modules/assets/use-asset-locations-data';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toAssetLocationFields } from '@/modules/assets/asset-location-fields';
import { useAssetLocationAccountOptions } from '@/modules/assets/use-asset-location-account-options';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useTagFieldOptions } from '@/modules/core/table/filters/shared/use-tag-field-options';

/**
 * The pill-bar fields for the per-asset locations table. Built inside a computed so the labels
 * track the locale: fields built once at setup keep the language they were created in until the
 * component remounts.
 *
 * Both option lists come from the unfiltered breakdown, so the bar offers exactly the locations and
 * accounts this asset is held in.
 */
export function useAssetLocationFields(rows: MaybeRefOrGetter<AssetLocation[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Location and address resolution is the same for every table filtering on them, so it comes from
  // one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const accounts = useAssetLocationAccountOptions(rows);
  const tagOptions = useTagFieldOptions();

  const locations = computed<string[]>(() => [...new Set(toValue(rows).map(row => row.location))]);

  return computed<FieldDef[]>(() => toAssetLocationFields(shared, t, {
    accounts,
    locations: (): string[] => get(locations),
    tags: (): TagFieldOption[] => get(tagOptions),
  }));
}
