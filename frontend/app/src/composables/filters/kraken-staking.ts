import { type MatchedKeyword, type SearchMatcher, assetSuggestions } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

enum KrakenStakingKeys {
  TYPE = 'type',
  ASSET = 'asset',
  START = 'start',
  END = 'end',
}

enum KrakenStakingValueKeys {
  TYPE = 'eventSubtypes',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp',
}

type Matcher = SearchMatcher<KrakenStakingKeys, KrakenStakingValueKeys>;

type Filters = MatchedKeyword<KrakenStakingValueKeys>;

export function useKrakenStakingFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoRetrieval();
  const { krakenStakingEventTypeData } = useKrakenStakingEventTypes();
  const { t } = useI18n();

  const getEventTypeIdentifier = (label: string): string =>
    get(krakenStakingEventTypeData).find(data => data.label === label)?.identifier ?? label;

  const matchers = computed<Matcher[]>(() => {
    const krakenStakingEventTypeValues = get(krakenStakingEventTypeData).map(data => data.label);

    return [
      {
        key: KrakenStakingKeys.ASSET,
        keyValue: KrakenStakingValueKeys.ASSET,
        description: t('kraken_staking_events.filter.asset'),
        asset: true,
        suggestions: assetSuggestions(assetSearch),
      },
      {
        key: KrakenStakingKeys.TYPE,
        keyValue: KrakenStakingValueKeys.TYPE,
        description: t('kraken_staking_events.filter.type').toString(),
        string: true,
        suggestions: (): string[] => krakenStakingEventTypeValues,
        validate: (option: string): boolean => krakenStakingEventTypeValues.includes(option as any),
        transformer: (type: string): string => getEventTypeIdentifier(type),
      },
      {
        key: KrakenStakingKeys.START,
        keyValue: KrakenStakingValueKeys.START,
        description: t('kraken_staking_events.filter.start_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        string: true,
        suggestions: (): string[] => [],
        validate: (value): boolean => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat))),
        transformer: (date: string): string => convertToTimestamp(date, get(dateInputFormat)).toString(),
      },
      {
        key: KrakenStakingKeys.END,
        keyValue: KrakenStakingValueKeys.END,
        description: t('kraken_staking_events.filter.end_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        string: true,
        suggestions: (): string[] => [],
        validate: (value): boolean => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat))),
        transformer: (date: string): string => convertToTimestamp(date, get(dateInputFormat)).toString(),
      },
    ];
  });

  return {
    filters,
    matchers,
  };
}
