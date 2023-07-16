import { type MatchedKeyword, type SearchMatcher } from '@/types/filtering';

enum KrakenStakingKeys {
  TYPE = 'type',
  ASSET = 'asset',
  START = 'start',
  END = 'end'
}

enum KrakenStakingValueKeys {
  TYPE = 'eventSubtypes',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp'
}

type Matcher = SearchMatcher<KrakenStakingKeys, KrakenStakingValueKeys>;

type Filters = MatchedKeyword<KrakenStakingValueKeys>;

export const useKrakenStakingFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoApi();
  const { krakenStakingEventTypeData } = useKrakenStakingEventTypes();
  const { t } = useI18n();

  const getEventTypeIdentifier = (label: string) =>
    get(krakenStakingEventTypeData).find(data => data.label === label)
      ?.identifier ?? label;

  const matchers: ComputedRef<Matcher[]> = computed(() => {
    const krakenStakingEventTypeValues = get(krakenStakingEventTypeData).map(
      data => data.label
    );

    return [
      {
        key: KrakenStakingKeys.ASSET,
        keyValue: KrakenStakingValueKeys.ASSET,
        description: t('kraken_staking_events.filter.asset'),
        asset: true,
        suggestions: async (value: string) => await assetSearch(value, 5)
      },
      {
        key: KrakenStakingKeys.TYPE,
        keyValue: KrakenStakingValueKeys.TYPE,
        description: t('kraken_staking_events.filter.type').toString(),
        string: true,
        suggestions: () => krakenStakingEventTypeValues,
        validate: (option: string) =>
          krakenStakingEventTypeValues.includes(option as any),
        transformer: (type: string) => getEventTypeIdentifier(type)
      },
      {
        key: KrakenStakingKeys.START,
        keyValue: KrakenStakingValueKeys.START,
        description: t('kraken_staking_events.filter.start_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        string: true,
        suggestions: () => [],
        validate: value =>
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, get(dateInputFormat))),
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: KrakenStakingKeys.END,
        keyValue: KrakenStakingValueKeys.END,
        description: t('kraken_staking_events.filter.end_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat))
        }).toString(),
        string: true,
        suggestions: () => [],
        validate: value =>
          value.length > 0 &&
          !isNaN(convertToTimestamp(value, get(dateInputFormat))),
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      }
    ];
  });

  const updateFilter = (newFilter: Filters) => {
    set(filters, newFilter);
  };

  return {
    filters,
    matchers,
    updateFilter
  };
};
