import type { MaybeRef } from '@vueuse/core';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { z } from 'zod/v4';

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

  const { t } = useI18n({ useScope: 'global' });

  const matchers = computed<Matcher[]>(() => [{
    description: t('assets.filter.name'),
    hint: t('assets.filter.name_hint'),
    key: CustomAssetFilterKeys.NAME,
    keyValue: CustomAssetFilterValueKeys.NAME,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  }, {
    description: t('assets.filter.type'),
    hint: t('assets.filter.type_hint'),
    key: CustomAssetFilterKeys.CUSTOM_ASSET_TYPE,
    keyValue: CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE,
    string: true,
    suggestions: (): string[] => get(suggestions),
    validate: (value: string): boolean => get(suggestions).includes(value),
  }]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE]: OptionalString,
    [CustomAssetFilterValueKeys.NAME]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
