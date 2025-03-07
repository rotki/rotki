import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { MaybeRef } from '@vueuse/core';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { CommaSeparatedStringSchema } from '@/types/route';
import { assetDeserializer, assetSuggestions } from '@/utils/assets';
import z from 'zod';

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
  const { assetInfo, assetSearch } = useAssetInfoRetrieval();

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('common.location'),
      key: ManualBalanceFilterKeys.LOCATION,
      keyValue: ManualBalanceFilterValueKeys.LOCATION,
      string: true,
      suggestions: (): string[] => get(locations),
      validate: (location): boolean => get(locations).includes(location),
    },
    {
      description: t('common.label'),
      key: ManualBalanceFilterKeys.LABEL,
      keyValue: ManualBalanceFilterValueKeys.LABEL,
      string: true,
      suggestions: (): string[] => [],
      validate: (type: string): boolean => !!type,
    },
    {
      asset: true,
      description: t('common.asset'),
      deserializer: assetDeserializer(assetInfo),
      key: ManualBalanceFilterKeys.ASSET,
      keyValue: ManualBalanceFilterValueKeys.ASSET,
      suggestions: assetSuggestions(assetSearch),
    },
  ]);

  const RouteFilterSchema = z.object({
    [ManualBalanceFilterValueKeys.ASSET]: z.string().optional(),
    [ManualBalanceFilterValueKeys.LABEL]: z.string().optional(),
    [ManualBalanceFilterValueKeys.LOCATION]: z.string().optional(),
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}

export const ManualBalancesFilterSchema = z.object({
  tags: CommaSeparatedStringSchema,
});
