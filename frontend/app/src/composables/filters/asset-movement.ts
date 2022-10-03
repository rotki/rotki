import { ComputedRef, Ref } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { MovementCategory } from '@/types/history/movements';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

enum AssetMovementFilterKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'start',
  END = 'end'
}

enum AssetMovementFilterValueKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp'
}

type Matcher = SearchMatcher<
  AssetMovementFilterKeys,
  AssetMovementFilterValueKeys
>;
type Filters = MatchedKeyword<AssetMovementFilterValueKeys>;

export const useAssetMovementFilters = () => {
  const filters: Ref<Filters> = ref({});

  const locationsStore = useAssociatedLocationsStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetSearch } = useAssetInfoApi();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: AssetMovementFilterKeys.ASSET,
      keyValue: AssetMovementFilterValueKeys.ASSET,
      description: tc('deposit_withdrawals.filter.asset'),
      asset: true,
      suggestions: async (value: string) => await assetSearch(value, 5)
    },
    {
      key: AssetMovementFilterKeys.ACTION,
      keyValue: AssetMovementFilterValueKeys.ACTION,
      description: tc('deposit_withdrawals.filter.action'),
      string: true,
      suggestions: () => MovementCategory.options,
      validate: type => (MovementCategory.options as string[]).includes(type)
    },
    {
      key: AssetMovementFilterKeys.START,
      keyValue: AssetMovementFilterValueKeys.START,
      description: tc('deposit_withdrawals.filter.start_date'),
      string: true,
      hint: tc('deposit_withdrawals.filter.date_hint', 0, {
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
      key: AssetMovementFilterKeys.END,
      keyValue: AssetMovementFilterValueKeys.END,
      description: tc('deposit_withdrawals.filter.end_date'),
      hint: tc('deposit_withdrawals.filter.date_hint', 0, {
        format: getDateInputISOFormat(get(dateInputFormat))
      }),
      string: true,
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
      key: AssetMovementFilterKeys.LOCATION,
      keyValue: AssetMovementFilterValueKeys.LOCATION,
      description: tc('deposit_withdrawals.filter.location'),
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
