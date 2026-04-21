import type { MatchedKeyword, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod/v4';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { dateDeserializer, dateRangeValidator, dateSerializer, getDateInputISOFormat } from '@/modules/core/common/data/date';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const OraclePriceFilterKeys = {
  END: 'end',
  FROM_ASSET: 'from_asset',
  SOURCE: 'source',
  START: 'start',
  TO_ASSET: 'to_asset',
} as const;

type OraclePriceFilterKey = typeof OraclePriceFilterKeys[keyof typeof OraclePriceFilterKeys];

const OraclePriceFilterValueKeys = {
  END: 'toTimestamp',
  FROM_ASSET: 'fromAsset',
  SOURCE: 'sourceType',
  START: 'fromTimestamp',
  TO_ASSET: 'toAsset',
} as const;

type OraclePriceFilterValueKey = typeof OraclePriceFilterValueKeys[keyof typeof OraclePriceFilterValueKeys];

export type Matcher = SearchMatcher<OraclePriceFilterKey, OraclePriceFilterValueKey>;

export type Filters = MatchedKeyword<OraclePriceFilterValueKey>;

const ORACLE_SOURCES: string[] = [
  PriceOracle.ALCHEMY,
  PriceOracle.BLOCKCHAIN,
  PriceOracle.COINGECKO,
  PriceOracle.CRYPTOCOMPARE,
  PriceOracle.DEFILLAMA,
  PriceOracle.FIAT,
  PriceOracle.MANUAL,
  PriceOracle.UNISWAP2,
  PriceOracle.UNISWAP3,
];

export function useOraclePricesFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch, getAssetInfo } = useAssetInfoRetrieval();
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

  const matchers = computed<Matcher[]>(() => [
    {
      asset: true,
      description: t('oracle_prices.filter.from_asset'),
      deserializer: getAssetInfo,
      key: OraclePriceFilterKeys.FROM_ASSET,
      keyValue: OraclePriceFilterValueKeys.FROM_ASSET,
      suggestions: assetSuggestions(assetSearch),
    },
    {
      asset: true,
      description: t('oracle_prices.filter.to_asset'),
      deserializer: getAssetInfo,
      key: OraclePriceFilterKeys.TO_ASSET,
      keyValue: OraclePriceFilterValueKeys.TO_ASSET,
      suggestions: assetSuggestions(assetSearch),
    },
    {
      description: t('oracle_prices.filter.source_type'),
      key: OraclePriceFilterKeys.SOURCE,
      keyValue: OraclePriceFilterValueKeys.SOURCE,
      string: true,
      strictMatching: true,
      suggestions: (): string[] => ORACLE_SOURCES,
      suggestionsToShow: -1,
      validate: (value: string): boolean => ORACLE_SOURCES.includes(value),
    },
    {
      description: t('oracle_prices.filter.from_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: OraclePriceFilterKeys.START,
      keyValue: OraclePriceFilterValueKeys.START,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.toTimestamp?.toString(), 'start'),
    },
    {
      description: t('oracle_prices.filter.to_date'),
      deserializer: dateDeserializer(dateInputFormat),
      hint: t('transactions.filter.date_hint', {
        format: getDateInputISOFormat(get(dateInputFormat)),
      }),
      key: OraclePriceFilterKeys.END,
      keyValue: OraclePriceFilterValueKeys.END,
      serializer: dateSerializer(dateInputFormat),
      string: true,
      suggestions: (): string[] => [],
      validate: dateRangeValidator(dateInputFormat, () => get(filters)?.fromTimestamp?.toString(), 'end'),
    },
  ]);

  const OptionalString = z.string().optional();

  const RouteFilterSchema = z.object({
    [OraclePriceFilterValueKeys.FROM_ASSET]: OptionalString,
    [OraclePriceFilterValueKeys.TO_ASSET]: OptionalString,
    [OraclePriceFilterValueKeys.SOURCE]: OptionalString,
    [OraclePriceFilterValueKeys.START]: OptionalString,
    [OraclePriceFilterValueKeys.END]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
