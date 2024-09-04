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
import type { FilterSchema } from '@/composables/filter-paginate';

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
  const { assetSearch, assetInfo } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [{
    key: AssetMovementFilterKeys.ASSET,
    keyValue: AssetMovementFilterValueKeys.ASSET,
    description: t('deposit_withdrawals.filter.asset'),
    asset: true,
    suggestions: assetSuggestions(assetSearch),
    deserializer: assetDeserializer(assetInfo),
  }, {
    key: AssetMovementFilterKeys.ACTION,
    keyValue: AssetMovementFilterValueKeys.ACTION,
    description: t('deposit_withdrawals.filter.action'),
    string: true,
    suggestions: (): MovementCategory[] => MovementCategory.options,
    validate: (type): boolean => (MovementCategory.options as string[]).includes(type),
  }, {
    key: AssetMovementFilterKeys.START,
    keyValue: AssetMovementFilterValueKeys.START,
    description: t('common.filter.start_date'),
    string: true,
    hint: t('common.filter.date_hint', {
      format: getDateInputISOFormat(get(dateInputFormat)),
    }),
    suggestions: (): string[] => [],
    validate: dateValidator(dateInputFormat),
    serializer: dateSerializer(dateInputFormat),
    deserializer: dateDeserializer(dateInputFormat),
  }, {
    key: AssetMovementFilterKeys.END,
    keyValue: AssetMovementFilterValueKeys.END,
    description: t('common.filter.end_date'),
    hint: t('common.filter.date_hint', {
      format: getDateInputISOFormat(get(dateInputFormat)),
    }),
    string: true,
    suggestions: (): string[] => [],
    validate: dateValidator(dateInputFormat),
    serializer: dateSerializer(dateInputFormat),
    deserializer: dateDeserializer(dateInputFormat),
  }, {
    key: AssetMovementFilterKeys.LOCATION,
    keyValue: AssetMovementFilterValueKeys.LOCATION,
    description: t('deposit_withdrawals.filter.location'),
    string: true,
    suggestions: (): string[] => get(associatedLocations),
    validate: (location): boolean => get(associatedLocations).includes(location),
  }] satisfies Matcher[]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AssetMovementFilterValueKeys.LOCATION]: OptionalString,
    [AssetMovementFilterValueKeys.ACTION]: OptionalString,
    [AssetMovementFilterValueKeys.ASSET]: OptionalString,
    [AssetMovementFilterValueKeys.START]: OptionalString,
    [AssetMovementFilterValueKeys.END]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
