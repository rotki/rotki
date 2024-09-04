import z from 'zod';
import { type MatchedKeyword, type SearchMatcher, assetDeserializer, assetSuggestions } from '@/types/filtering';
import type { MaybeRef } from '@vueuse/core';
import type { FilterSchema } from '@/composables/filter-paginate';

enum ManualBalanceFilterKeys {
  LOCATION = 'location',
  LABEL = 'label',
  ASSET = 'asset',
}

enum ManualBalanceFilterValueKeys {
  LOCATION = 'location',
  LABEL = 'label',
  ASSET = 'asset',
}

export type Matcher = SearchMatcher<ManualBalanceFilterKeys, ManualBalanceFilterValueKeys>;

export type Filters = MatchedKeyword<ManualBalanceFilterValueKeys>;

export function useManualBalanceFilter(locations: MaybeRef<string[]>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { t } = useI18n();
  const { assetSearch, assetInfo } = useAssetInfoRetrieval();

  const matchers = computed<Matcher[]>(() => [
    {
      key: ManualBalanceFilterKeys.LOCATION,
      keyValue: ManualBalanceFilterValueKeys.LOCATION,
      description: t('common.location'),
      string: true,
      suggestions: (): string[] => get(locations),
      validate: (location): boolean => get(locations).includes(location),
    },
    {
      key: ManualBalanceFilterKeys.LABEL,
      keyValue: ManualBalanceFilterValueKeys.LABEL,
      description: t('common.label'),
      string: true,
      suggestions: (): string[] => [],
      validate: (type: string): boolean => !!type,
    },
    {
      key: ManualBalanceFilterKeys.ASSET,
      keyValue: ManualBalanceFilterValueKeys.ASSET,
      description: t('common.asset'),
      asset: true,
      suggestions: assetSuggestions(assetSearch),
      deserializer: assetDeserializer(assetInfo),
    },
  ]);

  const RouteFilterSchema = z.object({
    [ManualBalanceFilterValueKeys.LOCATION]: z.string().optional(),
    [ManualBalanceFilterValueKeys.LABEL]: z.string().optional(),
    [ManualBalanceFilterValueKeys.ASSET]: z.string().optional(),
  });

  return {
    matchers,
    filters,
    RouteFilterSchema,
  };
}
