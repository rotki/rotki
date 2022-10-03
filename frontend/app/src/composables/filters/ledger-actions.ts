import { ComputedRef, Ref } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { LedgerActionType } from '@/types/ledger-actions';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

enum LedgerActionFilterKeys {
  ASSET = 'asset',
  TYPE = 'type',
  START = 'start',
  END = 'end',
  LOCATION = 'location'
}

enum LedgerActionFilterValueKeys {
  ASSET = 'asset',
  TYPE = 'type',
  START = 'fromTimestamp',
  END = 'toTimestamp',
  LOCATION = 'location'
}

type Matcher = SearchMatcher<
  LedgerActionFilterKeys,
  LedgerActionFilterValueKeys
>;
type Filters = MatchedKeyword<LedgerActionFilterValueKeys>;

export const useLedgerActionsFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { associatedLocations } = storeToRefs(useAssociatedLocationsStore());
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoApi();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: LedgerActionFilterKeys.ASSET,
      keyValue: LedgerActionFilterValueKeys.ASSET,
      description: tc('ledger_actions.filter.asset'),
      asset: true,
      suggestions: async (value: string) => await assetSearch(value, 5)
    },
    {
      key: LedgerActionFilterKeys.TYPE,
      keyValue: LedgerActionFilterValueKeys.TYPE,
      description: tc('ledger_actions.filter.action_type'),
      string: true,
      suggestions: () => [...Object.values(LedgerActionType)],
      validate: type =>
        ([...Object.values(LedgerActionType)] as string[]).includes(type)
    },
    {
      key: LedgerActionFilterKeys.START,
      keyValue: LedgerActionFilterValueKeys.START,
      description: tc('ledger_actions.filter.start_date'),
      string: true,
      hint: tc('ledger_actions.filter.date_hint', 0, {
        format: getDateInputISOFormat(get(dateInputFormat))
      }),
      suggestions: () => [],
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
      key: LedgerActionFilterKeys.END,
      keyValue: LedgerActionFilterValueKeys.END,
      description: tc('ledger_actions.filter.end_date'),
      string: true,
      hint: tc('ledger_actions.filter.date_hint', 0, {
        format: getDateInputISOFormat(get(dateInputFormat))
      }).toString(),
      suggestions: () => [],
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
      key: LedgerActionFilterKeys.LOCATION,
      keyValue: LedgerActionFilterValueKeys.LOCATION,
      description: tc('ledger_actions.filter.location'),
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
