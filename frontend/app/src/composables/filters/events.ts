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

enum HistoryEventFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol',
  EVENT_TYPE = 'event_type',
  LOCATION = 'location'
}

enum HistoryEventFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'counterparties',
  EVENT_TYPE = 'eventTypes',
  LOCATION = 'location'
}

export type Matcher = SearchMatcher<
  HistoryEventFilterKeys,
  HistoryEventFilterValueKeys
>;
export type Filters = MatchedKeyword<HistoryEventFilterValueKeys>;

export const useHistoryEventFilter = (disableProtocols: boolean) => {
  const filters: Ref<Filters> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { counterparties } = useHistoryEventMappings();
  const { assetSearch } = useAssetInfoApi();
  const { assetInfo } = useAssetInfoRetrieval();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => {
    const data: Matcher[] = [
      {
        key: HistoryEventFilterKeys.START,
        keyValue: HistoryEventFilterValueKeys.START,
        description: tc('transactions.filter.start_date'),
        string: true,
        hint: tc('transactions.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat)
      },
      {
        key: HistoryEventFilterKeys.END,
        keyValue: HistoryEventFilterValueKeys.END,
        description: tc('transactions.filter.end_date'),
        string: true,
        hint: tc('transactions.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat)
      },
      {
        key: HistoryEventFilterKeys.ASSET,
        keyValue: HistoryEventFilterValueKeys.ASSET,
        description: tc('transactions.filter.asset'),
        asset: true,
        suggestions: assetSuggestions(assetSearch),
        deserializer: assetDeserializer(assetInfo)
      }
    ];

    if (!disableProtocols) {
      data.push(
        {
          key: HistoryEventFilterKeys.PROTOCOL,
          keyValue: HistoryEventFilterValueKeys.PROTOCOL,
          description: tc('transactions.filter.protocol'),
          multiple: true,
          string: true,
          suggestions: () => get(counterparties),
          validate: (protocol: string) => !!protocol
        },
        {
          key: HistoryEventFilterKeys.LOCATION,
          keyValue: HistoryEventFilterValueKeys.LOCATION,
          description: tc('transactions.filter.location'),
          string: true,
          suggestions: () => get(associatedLocations),
          validate: location => !!location
        }
      );
    }

    return data;
  });

  const updateFilter = (newFilters: Filters) => {
    set(filters, {
      ...newFilters
    });
  };

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [HistoryEventFilterValueKeys.START]: OptionalString,
    [HistoryEventFilterValueKeys.END]: OptionalString,
    [HistoryEventFilterValueKeys.ASSET]: OptionalString,
    [HistoryEventFilterValueKeys.PROTOCOL]: z
      .array(z.string())
      .or(z.string())
      .transform(val => (Array.isArray(val) ? val : [val]))
      .optional(),
    [HistoryEventFilterValueKeys.LOCATION]: OptionalString
  });

  return {
    matchers,
    filters,
    updateFilter,
    RouteFilterSchema
  };
};
