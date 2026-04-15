import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/modules/table/filtering';
import { useSupportedChains } from '@/composables/info/chains';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { dateDeserializer, dateRangeValidator, dateSerializer, getDateInputISOFormat } from '@/utils/date';

const InternalTxConflictFilterKeys = {
  CHAIN: 'chain',
  FROM_TIMESTAMP: 'start',
  TO_TIMESTAMP: 'end',
} as const;

const InternalTxConflictFilterValueKeys = {
  CHAIN: 'chain',
  FROM_TIMESTAMP: 'fromTimestamp',
  TO_TIMESTAMP: 'toTimestamp',
} as const;

type InternalTxConflictFilterKey = typeof InternalTxConflictFilterKeys[keyof typeof InternalTxConflictFilterKeys];

type InternalTxConflictFilterValueKey = typeof InternalTxConflictFilterValueKeys[keyof typeof InternalTxConflictFilterValueKeys];

export type Matcher = SearchMatcher<InternalTxConflictFilterKey, InternalTxConflictFilterValueKey>;

export type Filters = MatchedKeywordWithBehaviour<InternalTxConflictFilterValueKey>;

export function useInternalTxConflictsFilter(): FilterSchema<Filters, Matcher> {
  const { t } = useI18n({ useScope: 'global' });
  const filters = ref<Filters>({});
  const { evmChainsData } = useSupportedChains();
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('internal_tx_conflicts.columns.chain'),
      key: InternalTxConflictFilterKeys.CHAIN,
      keyValue: InternalTxConflictFilterValueKeys.CHAIN,
      string: true,
      suggestions: (): string[] => get(evmChainsData).map(chain => chain.evmChainName),
      validate: (value: string): boolean => get(evmChainsData).some(chain => chain.evmChainName === value),
    },
    {
      description: t('transactions.filter.start_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: InternalTxConflictFilterKeys.FROM_TIMESTAMP,
      keyValue: InternalTxConflictFilterValueKeys.FROM_TIMESTAMP,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.toTimestamp?.toString(), 'start'),
    },
    {
      description: t('transactions.filter.end_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: InternalTxConflictFilterKeys.TO_TIMESTAMP,
      keyValue: InternalTxConflictFilterValueKeys.TO_TIMESTAMP,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.fromTimestamp?.toString(), 'end'),
    },
  ]);

  return {
    filters,
    matchers,
  };
}
