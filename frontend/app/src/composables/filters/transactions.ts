import { ComputedRef, Ref } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { useTransactions } from '@/store/history/transactions';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

enum TransactionFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol'
}

enum TransactionFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'protocols'
}

type Filters = MatchedKeyword<TransactionFilterValueKeys>;
type Matcher = SearchMatcher<TransactionFilterKeys, TransactionFilterValueKeys>;

export const useTransactionFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { counterparties } = storeToRefs(useTransactions());
  const { assetSearch } = useAssetInfoApi();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: TransactionFilterKeys.START,
      keyValue: TransactionFilterValueKeys.START,
      description: tc('transactions.filter.start_date'),
      string: true,
      hint: tc('transactions.filter.date_hint', 0, {
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
      key: TransactionFilterKeys.END,
      keyValue: TransactionFilterValueKeys.END,
      description: tc('transactions.filter.end_date'),
      string: true,
      hint: tc('transactions.filter.date_hint', 0, {
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
      key: TransactionFilterKeys.ASSET,
      keyValue: TransactionFilterValueKeys.ASSET,
      description: tc('transactions.filter.asset'),
      asset: true,
      suggestions: async (value: string) => await assetSearch(value, 5)
    },
    {
      key: TransactionFilterKeys.PROTOCOL,
      keyValue: TransactionFilterValueKeys.PROTOCOL,
      description: tc('transactions.filter.protocol'),
      multiple: true,
      string: true,
      suggestions: () => get(counterparties),
      validate: (protocol: string) => !!protocol
    }
  ]);

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  return {
    matchers,
    filters,
    updateFilter
  };
};
