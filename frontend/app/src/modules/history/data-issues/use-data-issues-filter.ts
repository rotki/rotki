import type { MatchedKeyword, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod/v4';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { arrayify } from '@/modules/core/common/data/array';
import { dateDeserializer, dateRangeValidator, dateSerializer, getDateInputISOFormat } from '@/modules/core/common/data/date';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

enum DataIssuesFilterKeys {
  STATE = 'state',
  KIND = 'kind',
  ASSET = 'asset',
  ACCOUNT = 'account',
  START = 'start',
  END = 'end',
}

enum DataIssuesFilterValueKeys {
  STATE = 'state',
  KIND = 'kind',
  ASSET = 'asset',
  ACCOUNT = 'locationLabel',
  START = 'fromTimestamp',
  END = 'toTimestamp',
}

export type Matcher = SearchMatcher<DataIssuesFilterKeys, DataIssuesFilterValueKeys>;

export type Filters = MatchedKeyword<DataIssuesFilterValueKeys>;

const STATES: string[] = Object.values(IssueState);
const KINDS: string[] = Object.values(IssueKind);

export function useDataIssuesFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch, getAssetInfo } = useAssetInfoRetrieval();
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('data_issues.filter.state'),
      key: DataIssuesFilterKeys.STATE,
      keyValue: DataIssuesFilterValueKeys.STATE,
      multiple: true,
      string: true,
      strictMatching: true,
      suggestions: (): string[] => STATES,
      suggestionsToShow: -1,
      validate: (value: string): boolean => STATES.includes(value),
    },
    {
      description: t('data_issues.filter.kind'),
      key: DataIssuesFilterKeys.KIND,
      keyValue: DataIssuesFilterValueKeys.KIND,
      multiple: true,
      string: true,
      strictMatching: true,
      suggestions: (): string[] => KINDS,
      suggestionsToShow: -1,
      validate: (value: string): boolean => KINDS.includes(value),
    },
    {
      asset: true,
      description: t('data_issues.filter.asset'),
      deserializer: getAssetInfo,
      key: DataIssuesFilterKeys.ASSET,
      keyValue: DataIssuesFilterValueKeys.ASSET,
      suggestions: assetSuggestions(assetSearch),
    },
    {
      description: t('data_issues.filter.account'),
      key: DataIssuesFilterKeys.ACCOUNT,
      keyValue: DataIssuesFilterValueKeys.ACCOUNT,
      string: true,
      suggestions: (): string[] => [],
      validate: (value: string): boolean => value.length > 0,
    },
    {
      description: t('data_issues.filter.start_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: DataIssuesFilterKeys.START,
      keyValue: DataIssuesFilterValueKeys.START,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.toTimestamp?.toString(), 'start'),
    },
    {
      description: t('data_issues.filter.end_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: DataIssuesFilterKeys.END,
      keyValue: DataIssuesFilterValueKeys.END,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.fromTimestamp?.toString(), 'end'),
    },
  ]);

  const OptionalMultipleString = z.array(z.string()).or(z.string()).transform(arrayify).optional();
  const OptionalString = z.string().optional();

  const RouteFilterSchema = z.object({
    [DataIssuesFilterValueKeys.ACCOUNT]: OptionalString,
    [DataIssuesFilterValueKeys.ASSET]: OptionalString,
    [DataIssuesFilterValueKeys.END]: OptionalString,
    [DataIssuesFilterValueKeys.KIND]: OptionalMultipleString,
    [DataIssuesFilterValueKeys.START]: OptionalString,
    [DataIssuesFilterValueKeys.STATE]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
