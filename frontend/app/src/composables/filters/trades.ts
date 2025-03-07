import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type {
  MatchedKeyword,
  SearchMatcher,

} from '@/types/filtering';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoryStore } from '@/store/history';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { TradeType } from '@/types/history/trade';
import { assetDeserializer, assetSuggestions, dateDeserializer, dateSerializer, dateValidator } from '@/utils/assets';
import { getDateInputISOFormat } from '@/utils/date';
import { z } from 'zod';

enum TradeFilterKeys {
  BASE = 'base',
  QUOTE = 'quote',
  ACTION = 'action',
  START = 'start',
  END = 'end',
  LOCATION = 'location',
}

enum TradeFilterValueKeys {
  BASE = 'baseAsset',
  QUOTE = 'quoteAsset',
  ACTION = 'tradeType',
  START = 'fromTimestamp',
  END = 'toTimestamp',
  LOCATION = 'location',
}

export type Matcher = SearchMatcher<TradeFilterKeys, TradeFilterValueKeys>;

export type Filters = MatchedKeyword<TradeFilterValueKeys>;

export function useTradeFilters(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetInfo, assetSearch } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [
    {
      asset: true,
      description: t('closed_trades.filter.base_asset'),
      deserializer: assetDeserializer(assetInfo),
      key: TradeFilterKeys.BASE,
      keyValue: TradeFilterValueKeys.BASE,
      suggestions: assetSuggestions(assetSearch),
    },
    {
      asset: true,
      description: t('closed_trades.filter.quote_asset'),
      deserializer: assetDeserializer(assetInfo),
      key: TradeFilterKeys.QUOTE,
      keyValue: TradeFilterValueKeys.QUOTE,
      suggestions: assetSuggestions(assetSearch),
    },
    {
      description: t('closed_trades.filter.trade_type'),
      key: TradeFilterKeys.ACTION,
      keyValue: TradeFilterValueKeys.ACTION,
      string: true,
      suggestions: (): TradeType[] => Object.values(TradeType),
      validate: (type): boolean => Object.values(TradeType).map(item => item.toString()).includes(type),
    },
    {
      description: t('closed_trades.filter.start_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('closed_trades.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: TradeFilterKeys.START,
      keyValue: TradeFilterValueKeys.START,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateValidator(dateInputFormat),
    },
    {
      description: t('closed_trades.filter.end_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('closed_trades.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: TradeFilterKeys.END,
      keyValue: TradeFilterValueKeys.END,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateValidator(dateInputFormat),
    },
    {
      description: t('closed_trades.filter.location'),
      key: TradeFilterKeys.LOCATION,
      keyValue: TradeFilterValueKeys.LOCATION,
      string: true,
      suggestions: (): string[] => get(associatedLocations),
      validate: (location): boolean => get(associatedLocations).includes(location),
    },
  ] satisfies Matcher[]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [TradeFilterValueKeys.ACTION]: OptionalString,
    [TradeFilterValueKeys.BASE]: OptionalString,
    [TradeFilterValueKeys.END]: OptionalString,
    [TradeFilterValueKeys.LOCATION]: OptionalString,
    [TradeFilterValueKeys.QUOTE]: OptionalString,
    [TradeFilterValueKeys.START]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
