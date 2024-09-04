import { z } from 'zod';
import type { MaybeRef } from '@vueuse/core';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

enum CustomAssetFilterKeys {
  NAME = 'name',
  CUSTOM_ASSET_TYPE = 'type',
}

enum CustomAssetFilterValueKeys {
  NAME = 'name',
  CUSTOM_ASSET_TYPE = 'custom_asset_type',
}

export type Matcher = SearchMatcher<CustomAssetFilterKeys, CustomAssetFilterValueKeys>;

export type Filters = MatchedKeyword<CustomAssetFilterValueKeys>;

export function useCustomAssetFilter(suggestions: MaybeRef<string[]>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [{
    key: CustomAssetFilterKeys.NAME,
    keyValue: CustomAssetFilterValueKeys.NAME,
    description: t('assets.filter.name'),
    string: true,
    suggestions: (): string[] => [],
    hint: t('assets.filter.name_hint'),
    validate: (): boolean => true,
  }, {
    key: CustomAssetFilterKeys.CUSTOM_ASSET_TYPE,
    keyValue: CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE,
    description: t('assets.filter.type'),
    string: true,
    suggestions: (): string[] => get(suggestions),
    hint: t('assets.filter.type_hint'),
    validate: (value: string): boolean => get(suggestions).includes(value),
  }]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [CustomAssetFilterValueKeys.NAME]: OptionalString,
    [CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
