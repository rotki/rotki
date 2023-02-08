import { type ComputedRef, type Ref } from 'vue';
import { type MatchedKeyword, type SearchMatcher } from '@/types/filtering';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

enum TransactionFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol',
  EVENT_TYPE = 'event_type',
  EVM_CHAIN = 'chain'
}

enum TransactionFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'protocols',
  EVENT_TYPE = 'eventTypes',
  EVM_CHAIN = 'evmChain'
}

type Filters = MatchedKeyword<TransactionFilterValueKeys>;
type Matcher = SearchMatcher<TransactionFilterKeys, TransactionFilterValueKeys>;

export const useTransactionFilter = (disableProtocols: boolean) => {
  const filters: Ref<Filters> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { counterparties } = storeToRefs(useTransactionStore());
  const { txEvmChains } = useSupportedChains();
  const { assetSearch } = useAssetInfoApi();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => {
    const data: Matcher[] = [
      {
        key: TransactionFilterKeys.START,
        keyValue: TransactionFilterValueKeys.START,
        description: tc('transactions.filter.start_date'),
        string: true,
        hint: tc('transactions.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        suggestions: () => [],
        validate: (value: string) => {
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
        validate: (value: string) => {
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
      }
    ];

    if (!disableProtocols) {
      data.push(
        {
          key: TransactionFilterKeys.PROTOCOL,
          keyValue: TransactionFilterValueKeys.PROTOCOL,
          description: tc('transactions.filter.protocol'),
          multiple: true,
          string: true,
          suggestions: () => get(counterparties),
          validate: (protocol: string) => !!protocol
        },
        {
          key: TransactionFilterKeys.EVM_CHAIN,
          keyValue: TransactionFilterValueKeys.EVM_CHAIN,
          description: tc('transactions.filter.chain'),
          string: true,
          suggestions: () => get(txEvmChains).map(x => x.evmChainName),
          validate: (chain: string) => !!chain
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

  return {
    matchers,
    filters,
    updateFilter
  };
};
