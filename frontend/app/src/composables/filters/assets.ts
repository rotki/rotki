import type { Ref } from 'vue';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { z } from 'zod/v4';
import { useSupportedChains } from '@/composables/info/chains';
import { SOLANA_CHAIN } from '@/types/asset';
import { arrayify } from '@/utils/array';

enum AssetFilterKeys {
  IDENTIFIER = 'identifier',
  ASSET_TYPE = 'type',
  SYMBOL = 'symbol',
  NAME = 'name',
  CHAIN = 'chain',
  ADDRESS = 'address',
}

enum AssetFilterValueKeys {
  IDENTIFIER = 'identifiers',
  ASSET_TYPE = 'assetType',
  SYMBOL = 'symbol',
  NAME = 'name',
  CHAIN = 'evmChain',
  ADDRESS = 'address',
}

export type Matcher = SearchMatcher<AssetFilterKeys, AssetFilterValueKeys>;

export type Filters = MatchedKeyword<AssetFilterValueKeys>;

export function useAssetFilter(assetTypes: Ref<string[]>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

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
    ...(!get(filters).evmChain
      ? [{
        description: t('assets.filter.asset_type'),
        key: AssetFilterKeys.ASSET_TYPE,
        keyValue: AssetFilterValueKeys.ASSET_TYPE,
        string: true,
        suggestions: (): string[] => get(assetTypes),
        suggestionsToShow: -1,
        validate: (): true => true,
      }] satisfies Matcher[]
      : []),
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
    ...(!get(filters).assetType
      ? [{
        description: t('assets.filter.chain'),
        key: AssetFilterKeys.CHAIN,
        keyValue: AssetFilterValueKeys.CHAIN,
        string: true,
        suggestions: (): string[] => [...get(allEvmChains).map(x => x.name), SOLANA_CHAIN],
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
    [AssetFilterValueKeys.ASSET_TYPE]: OptionalString,
    [AssetFilterValueKeys.CHAIN]: OptionalString,
    [AssetFilterValueKeys.IDENTIFIER]: OptionalMultipleString,
    [AssetFilterValueKeys.NAME]: OptionalString,
    [AssetFilterValueKeys.SYMBOL]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
