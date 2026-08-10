import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';

/** The wire keys the custom assets table filters on, which the URL carries too. */
export const CustomAssetFilterKeys = {
  CUSTOM_ASSET_TYPE: 'custom_asset_type',
  NAME: 'name',
} as const;

export type CustomAssetFilterKey = typeof CustomAssetFilterKeys[keyof typeof CustomAssetFilterKeys];

export type Filters = MatchedKeyword<CustomAssetFilterKey>;

export function useCustomAssetFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
  };
}
