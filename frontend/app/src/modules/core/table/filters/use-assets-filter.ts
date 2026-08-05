import type { MaybeRefOrGetter } from 'vue';
import type { MatchedKeyword, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod';
import { AssetFlag, HYPERLIQUID_CORE_CHAIN, SOLANA_CHAIN } from '@/modules/assets/types';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

const assetFlags: string[] = Object.values(AssetFlag);

enum AssetFilterKeys {
  ASSET_FLAG = 'flag',
  IDENTIFIER = 'identifier',
  ASSET_TYPE = 'type',
  SYMBOL = 'symbol',
  NAME = 'name',
  CHAIN = 'chain',
  ADDRESS = 'address',
}

enum AssetFilterValueKeys {
  ASSET_FLAG = 'assetFlag',
  IDENTIFIER = 'identifiers',
  ASSET_TYPE = 'assetType',
  SYMBOL = 'symbol',
  NAME = 'name',
  CHAIN = 'evmChain',
  ADDRESS = 'address',
}

export type Matcher = SearchMatcher<AssetFilterKeys, AssetFilterValueKeys>;

export type Filters = MatchedKeyword<AssetFilterValueKeys>;

export function useAssetFilter(assetTypes: MaybeRefOrGetter<string[]>): FilterSchema<Filters, Matcher> {
  const modelFilters = ref<Filters>({});

  const { allEvmChains } = useSupportedChains();
  const { t } = useI18n({ useScope: 'global' });

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('assets.filter.identifier'),
      hint: t('assets.filter.identifier_hint'),
      key: AssetFilterKeys.IDENTIFIER,
      keyValue: AssetFilterValueKeys.IDENTIFIER,
      multiple: false,
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    ...(!get(modelFilters).evmChain
      ? [{
        description: t('assets.filter.asset_type'),
        key: AssetFilterKeys.ASSET_TYPE,
        keyValue: AssetFilterValueKeys.ASSET_TYPE,
        string: true,
        suggestions: (): string[] => toValue(assetTypes),
        suggestionsToShow: -1,
        validate: (): true => true,
      }] satisfies Matcher[]
      : []),
    {
      description: t('assets.filter.asset_flag'),
      hint: t('assets.filter.asset_flag_hint'),
      key: AssetFilterKeys.ASSET_FLAG,
      keyValue: AssetFilterValueKeys.ASSET_FLAG,
      strictMatching: true,
      string: true,
      suggestions: (): string[] => assetFlags,
      suggestionsToShow: -1,
      validate: (flag: string): boolean => assetFlags.includes(flag),
    },
    {
      description: t('assets.filter.symbol'),
      hint: t('assets.filter.symbol_hint'),
      key: AssetFilterKeys.SYMBOL,
      keyValue: AssetFilterValueKeys.SYMBOL,
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      description: t('assets.filter.name'),
      hint: t('assets.filter.name_hint'),
      key: AssetFilterKeys.NAME,
      keyValue: AssetFilterValueKeys.NAME,
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    ...(!get(modelFilters).assetType
      ? [{
        description: t('assets.filter.chain'),
        key: AssetFilterKeys.CHAIN,
        keyValue: AssetFilterValueKeys.CHAIN,
        string: true,
        suggestions: (): string[] => [
          ...get(allEvmChains).map(x => x.name),
          HYPERLIQUID_CORE_CHAIN,
          SOLANA_CHAIN,
        ],
        validate: (chain: string): boolean => !!chain,
      }] satisfies Matcher[]
      : []),
    {
      description: t('assets.filter.address'),
      hint: t('assets.filter.address_hint'),
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => !!address,
    },
  ]);

  const OptionalString = z.string().optional();
  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [AssetFilterValueKeys.ADDRESS]: OptionalString,
    [AssetFilterValueKeys.ASSET_FLAG]: OptionalString,
    [AssetFilterValueKeys.ASSET_TYPE]: OptionalString,
    [AssetFilterValueKeys.CHAIN]: OptionalString,
    [AssetFilterValueKeys.IDENTIFIER]: OptionalMultipleString,
    [AssetFilterValueKeys.NAME]: OptionalString,
    [AssetFilterValueKeys.SYMBOL]: OptionalString,
  });

  return {
    filters: modelFilters,
    matchers,
    RouteFilterSchema,
  };
}
