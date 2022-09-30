import { MaybeRef } from '@vueuse/core';
import { ComputedRef, Ref } from 'vue';
import { MatchedKeyword, SearchMatcher } from '@/types/filtering';

enum CustomAssetFilterKeys {
  NAME = 'name',
  CUSTOM_ASSET_TYPE = 'type'
}

enum CustomAssetFilterValueKeys {
  NAME = 'name',
  CUSTOM_ASSET_TYPE = 'custom_asset_type'
}

type AssetMatcher = SearchMatcher<
  CustomAssetFilterKeys,
  CustomAssetFilterValueKeys
>;
type Matches = MatchedKeyword<CustomAssetFilterValueKeys>;

export const useCustomAssetFilter = (suggestions: MaybeRef<string[]>) => {
  const filters: Ref<Matches> = ref({});

  const { tc } = useI18n();

  const matchers: ComputedRef<AssetMatcher[]> = computed(() => [
    {
      key: CustomAssetFilterKeys.NAME,
      keyValue: CustomAssetFilterValueKeys.NAME,
      description: tc('assets.filter.name'),
      suggestions: () => [],
      hint: tc('assets.filter.name_hint'),
      validate: () => true
    },
    {
      key: CustomAssetFilterKeys.CUSTOM_ASSET_TYPE,
      keyValue: CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE,
      description: tc('assets.filter.type'),
      suggestions: () => get(suggestions),
      hint: tc('assets.filter.type_hint'),
      validate: (value: string) => get(suggestions).includes(value)
    }
  ]);

  const updateFilter = (newFilters: Matches) => {
    set(filters, newFilters);
  };

  return {
    filters,
    matchers,
    updateFilter
  };
};
