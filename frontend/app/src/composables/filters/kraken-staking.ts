import { type MatchedKeyword, type SearchMatcher, assetSuggestions } from '@/types/filtering';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useKrakenStakingEventTypes } from '@/composables/staking/kraken-events';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';

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
        asset: true,
        description: t('kraken_staking_events.filter.asset'),
        key: KrakenStakingKeys.ASSET,
        keyValue: KrakenStakingValueKeys.ASSET,
        suggestions: assetSuggestions(assetSearch),
      },
      {
        description: t('kraken_staking_events.filter.type'),
        key: KrakenStakingKeys.TYPE,
        keyValue: KrakenStakingValueKeys.TYPE,
        string: true,
        suggestions: (): string[] => krakenStakingEventTypeValues,
        transformer: (type: string): string => getEventTypeIdentifier(type),
        validate: (option: string): boolean => krakenStakingEventTypeValues.includes(option as any),
      },
      {
        description: t('kraken_staking_events.filter.start_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        key: KrakenStakingKeys.START,
        keyValue: KrakenStakingValueKeys.START,
        string: true,
        suggestions: (): string[] => [],
        transformer: (date: string): string => convertToTimestamp(date, get(dateInputFormat)).toString(),
        validate: (value): boolean => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat))),
      },
      {
        description: t('kraken_staking_events.filter.end_date'),
        hint: t('kraken_staking_events.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat)),
        }),
        key: KrakenStakingKeys.END,
        keyValue: KrakenStakingValueKeys.END,
        string: true,
        suggestions: (): string[] => [],
        transformer: (date: string): string => convertToTimestamp(date, get(dateInputFormat)).toString(),
        validate: (value): boolean => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat))),
      },
    ];
  });

  return {
    filters,
    matchers,
  };
}
