import type { MaybeRefOrGetter } from 'vue';
import type { Filters } from '@/modules/accounts/manual-balances/use-manual-balances-filter';
import type { AssetsWithId } from '@/modules/assets/types';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toManualBalanceFields } from '@/modules/accounts/manual-balances/manual-balance-fields';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useTagFieldOptions } from '@/modules/core/table/filters/shared/use-tag-field-options';

/** The pill-bar fields for the manual balances table. */
export function useManualBalanceFields(
  locations: MaybeRefOrGetter<string[]>,
  filters: MaybeRefOrGetter<Filters>,
): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const tagOptions = useTagFieldOptions();
  const { assetSearch } = useAssetInfoRetrieval();

  /**
   * The asset search is scoped to the picked location, so a location that names a chain searches
   * that chain's assets. The filter holds one location but the bag types it as one-or-many.
   */
  const location = computed<string | undefined>(() => {
    const picked = toValue(filters)?.location;
    return (Array.isArray(picked) ? picked[0] : picked)?.toString();
  });

  const search = computed(() => assetSuggestions(assetSearch, get(location)));
  const searchAsset = async (value: string): Promise<AssetsWithId> => get(search)(value);

  return toManualBalanceFields(shared, t, {
    locations: (): string[] => toValue(locations),
    searchAsset,
    tags: (): TagFieldOption[] => get(tagOptions),
  });
}
