import { type ComputedRef, type Ref } from 'vue';
import { type MatchedKeyword, type SearchMatcher } from '@/types/filtering';
import { TradeType } from '@/types/history/trade/trades';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

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

type Matcher = SearchMatcher<TradeFilterKeys, TradeFilterValueKeys>;
type Filters = MatchedKeyword<TradeFilterValueKeys>;

export const useTradeFilters = () => {
  const filters: Ref<Filters> = ref({});

  const { associatedLocations } = storeToRefs(useAssociatedLocationsStore());
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoApi();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: TradeFilterKeys.BASE,
      keyValue: TradeFilterValueKeys.BASE,
      description: tc('closed_trades.filter.base_asset'),
      asset: true,
      suggestions: async (value: string) => await assetSearch(value, 5)
    },
    {
      key: TradeFilterKeys.QUOTE,
      keyValue: TradeFilterValueKeys.QUOTE,
      description: tc('closed_trades.filter.quote_asset'),
      asset: true,
      suggestions: async (value: string) => await assetSearch(value, 5)
    },
    {
      key: TradeFilterKeys.ACTION,
      keyValue: TradeFilterValueKeys.ACTION,
      description: tc('closed_trades.filter.trade_type'),
      string: true,
      suggestions: () => TradeType.options,
      validate: type => (TradeType.options as string[]).includes(type)
    },
    {
      key: TradeFilterKeys.START,
      keyValue: TradeFilterValueKeys.START,
      description: tc('closed_trades.filter.start_date'),
      string: true,
      suggestions: () => [],
      hint: tc('closed_trades.filter.date_hint', 0, {
        format: getDateInputISOFormat(get(dateInputFormat))
      }),
      validate: value => {
        return (
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, get(dateInputFormat)))
        );
      },
      transformer: (date: string) =>
        convertToTimestamp(date, get(dateInputFormat)).toString()
    },
    {
      key: TradeFilterKeys.END,
      keyValue: TradeFilterValueKeys.END,
      description: tc('closed_trades.filter.end_date'),
      string: true,
      suggestions: () => [],
      hint: tc('closed_trades.filter.date_hint', 0, {
        format: getDateInputISOFormat(get(dateInputFormat))
      }),
      validate: value => {
        return (
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, get(dateInputFormat)))
        );
      },
      transformer: (date: string) =>
        convertToTimestamp(date, get(dateInputFormat)).toString()
    },
    {
      key: TradeFilterKeys.LOCATION,
      keyValue: TradeFilterValueKeys.LOCATION,
      description: tc('closed_trades.filter.location'),
      string: true,
      suggestions: () => get(associatedLocations),
      validate: location => get(associatedLocations).includes(location as any)
    }
  ]);

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  return {
    filters,
    matchers,
    updateFilter
  };
};
