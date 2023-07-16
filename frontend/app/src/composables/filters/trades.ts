import { z } from 'zod';
import {
  type MatchedKeyword,
  type SearchMatcher,
  assetDeserializer,
  assetSuggestions,
  dateDeserializer,
  dateSerializer,
  dateValidator
} from '@/types/filtering';
import { TradeType } from '@/types/history/trade';

enum TradeFilterKeys {
  BASE = 'base',
  QUOTE = 'quote',
  ACTION = 'action',
  START = 'start',
  END = 'end',
  LOCATION = 'location'
}

enum TradeFilterValueKeys {
  BASE = 'baseAsset',
  QUOTE = 'quoteAsset',
  ACTION = 'tradeType',
  START = 'fromTimestamp',
  END = 'toTimestamp',
  LOCATION = 'location'
}

export type Matcher = SearchMatcher<TradeFilterKeys, TradeFilterValueKeys>;

export type Filters = MatchedKeyword<TradeFilterValueKeys>;

export const useTradeFilters = () => {
  const filters: Ref<Filters> = ref({});

  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoApi();
  const { assetInfo } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(
    () =>
      [
        {
          key: TradeFilterKeys.BASE,
          keyValue: TradeFilterValueKeys.BASE,
          description: t('closed_trades.filter.base_asset'),
          asset: true,
          suggestions: assetSuggestions(assetSearch),
          deserializer: assetDeserializer(assetInfo)
        },
        {
          key: TradeFilterKeys.QUOTE,
          keyValue: TradeFilterValueKeys.QUOTE,
          description: t('closed_trades.filter.quote_asset'),
          asset: true,
          suggestions: assetSuggestions(assetSearch),
          deserializer: assetDeserializer(assetInfo)
        },
        {
          key: TradeFilterKeys.ACTION,
          keyValue: TradeFilterValueKeys.ACTION,
          description: t('closed_trades.filter.trade_type'),
          string: true,
          suggestions: () => TradeType.options,
          validate: type => (TradeType.options as string[]).includes(type)
        },
        {
          key: TradeFilterKeys.START,
          keyValue: TradeFilterValueKeys.START,
          description: t('closed_trades.filter.start_date'),
          string: true,
          suggestions: () => [],
          hint: t('closed_trades.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          }),
          validate: dateValidator(dateInputFormat),
          serializer: dateSerializer(dateInputFormat),
          deserializer: dateDeserializer(dateInputFormat)
        },
        {
          key: TradeFilterKeys.END,
          keyValue: TradeFilterValueKeys.END,
          description: t('closed_trades.filter.end_date'),
          string: true,
          suggestions: () => [],
          hint: t('closed_trades.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          }),
          validate: dateValidator(dateInputFormat),
          serializer: dateSerializer(dateInputFormat),
          deserializer: dateDeserializer(dateInputFormat)
        },
        {
          key: TradeFilterKeys.LOCATION,
          keyValue: TradeFilterValueKeys.LOCATION,
          description: t('closed_trades.filter.location'),
          string: true,
          suggestions: () => get(associatedLocations),
          validate: location =>
            get(associatedLocations).includes(location as any)
        }
      ] satisfies Matcher[]
  );

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [TradeFilterValueKeys.BASE]: OptionalString,
    [TradeFilterValueKeys.QUOTE]: OptionalString,
    [TradeFilterValueKeys.ACTION]: OptionalString,
    [TradeFilterValueKeys.START]: OptionalString,
    [TradeFilterValueKeys.END]: OptionalString,
    [TradeFilterValueKeys.LOCATION]: OptionalString
  });

  return {
    filters,
    matchers,
    updateFilter,
    RouteFilterSchema
  };
};
