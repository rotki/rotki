import { Ref } from 'vue';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
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

export const useTransactionFilter = () => {
  const filters: Ref<MatchedKeyword<TransactionFilterValueKeys>> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { assetIdentifierForSymbol } = useAssetInfoRetrieval();
  const { counterparties } = storeToRefs(useTransactions());
  const i18n = useI18n();

  const matchers = computed<
    SearchMatcher<TransactionFilterKeys, TransactionFilterValueKeys>[]
  >(() => [
    {
      key: TransactionFilterKeys.START,
      keyValue: TransactionFilterValueKeys.START,
      description: i18n.t('transactions.filter.start_date').toString(),
      suggestions: () => [],
      hint: i18n
        .t('transactions.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat))
        })
        .toString(),
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
      description: i18n.t('transactions.filter.end_date').toString(),
      suggestions: () => [],
      hint: i18n
        .t('transactions.filter.date_hint', {
          format: getDateInputISOFormat(get(dateInputFormat))
        })
        .toString(),
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
      description: i18n.t('transactions.filter.asset').toString(),
      suggestions: () => [],
      validate: () => true,
      transformer: (asset: string) => assetIdentifierForSymbol(asset) ?? ''
    },
    {
      key: TransactionFilterKeys.PROTOCOL,
      keyValue: TransactionFilterValueKeys.PROTOCOL,
      description: i18n.t('transactions.filter.protocol').toString(),
      multiple: true,
      suggestions: () => get(counterparties),
      validate: (protocol: string) => !!protocol
    }
  ]);

  const updateFilter = (newFilters: MatchedKeyword<TransactionFilterKeys>) => {
    set(filters, newFilters);
  };

  return {
    matchers,
    filters,
    updateFilter
  };
};
