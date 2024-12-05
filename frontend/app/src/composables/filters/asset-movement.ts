import { z } from 'zod';
import {
  type MatchedKeyword,
  type SearchMatcher,
  assetDeserializer,
  assetSuggestions,
  dateDeserializer,
  dateSerializer,
  dateValidator,
} from '@/types/filtering';
import { MovementCategory } from '@/types/history/asset-movements';
import { getDateInputISOFormat } from '@/utils/date';
import { useHistoryStore } from '@/store/history';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';

enum AssetMovementFilterKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'start',
  END = 'end',
}

enum AssetMovementFilterValueKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp',
}

export type Matcher = SearchMatcher<AssetMovementFilterKeys, AssetMovementFilterValueKeys>;

export type Filters = MatchedKeyword<AssetMovementFilterValueKeys>;

export function useAssetMovementFilters(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const locationsStore = useHistoryStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetInfo, assetSearch } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [{
    asset: true,
    description: t('deposit_withdrawals.filter.asset'),
    deserializer: assetDeserializer(assetInfo),
    key: AssetMovementFilterKeys.ASSET,
    keyValue: AssetMovementFilterValueKeys.ASSET,
    suggestions: assetSuggestions(assetSearch),
  }, {
    description: t('deposit_withdrawals.filter.action'),
    key: AssetMovementFilterKeys.ACTION,
    keyValue: AssetMovementFilterValueKeys.ACTION,
    string: true,
    suggestions: (): MovementCategory[] => MovementCategory.options,
    validate: (type): boolean => (MovementCategory.options as string[]).includes(type),
  }, {
    description: t('common.filter.start_date'),
    deserializer: dateDeserializer(dateInputFormat),
    hint: t('common.filter.date_hint', {
      format: getDateInputISOFormat(get(dateInputFormat)),
    }),
    key: AssetMovementFilterKeys.START,
    keyValue: AssetMovementFilterValueKeys.START,
    serializer: dateSerializer(dateInputFormat),
    string: true,
    suggestions: (): string[] => [],
    validate: dateValidator(dateInputFormat),
  }, {
    description: t('common.filter.end_date'),
    deserializer: dateDeserializer(dateInputFormat),
    hint: t('common.filter.date_hint', {
      format: getDateInputISOFormat(get(dateInputFormat)),
    }),
    key: AssetMovementFilterKeys.END,
    keyValue: AssetMovementFilterValueKeys.END,
    serializer: dateSerializer(dateInputFormat),
    string: true,
    suggestions: (): string[] => [],
    validate: dateValidator(dateInputFormat),
  }, {
    description: t('deposit_withdrawals.filter.location'),
    key: AssetMovementFilterKeys.LOCATION,
    keyValue: AssetMovementFilterValueKeys.LOCATION,
    string: true,
    suggestions: (): string[] => get(associatedLocations),
    validate: (location): boolean => get(associatedLocations).includes(location),
  }] satisfies Matcher[]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AssetMovementFilterValueKeys.ACTION]: OptionalString,
    [AssetMovementFilterValueKeys.ASSET]: OptionalString,
    [AssetMovementFilterValueKeys.END]: OptionalString,
    [AssetMovementFilterValueKeys.LOCATION]: OptionalString,
    [AssetMovementFilterValueKeys.START]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
