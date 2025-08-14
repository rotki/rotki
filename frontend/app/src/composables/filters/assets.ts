import type { Ref } from 'vue';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { z } from 'zod/v4';
import { useSupportedChains } from '@/composables/info/chains';
import { arrayify } from '@/utils/array';

enum AssetFilterKeys {
  IDENTIFIER = 'identifier',
  ASSET_TYPE = 'type',
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'chain',
  ADDRESS = 'address',
}

enum AssetFilterValueKeys {
  IDENTIFIER = 'identifiers',
  ASSET_TYPE = 'assetType',
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'evmChain',
  ADDRESS = 'address',
}

export type Matcher = SearchMatcher<AssetFilterKeys, AssetFilterValueKeys>;

export type Filters = MatchedKeyword<AssetFilterValueKeys>;

export function useAssetFilter(assetTypes: Ref<string[]>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { allEvmChains } = useSupportedChains();
  const { t } = useI18n({ useScope: 'global' });

  const matchers = computed<Matcher[]>(() => {
    const matcherList: Matcher[] = [
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
    ];

    // Only add asset_type matcher if evmChain filter is not set
    if (!get(filters).evmChain) {
      matcherList.push({
        description: t('assets.filter.asset_type'),
        key: AssetFilterKeys.ASSET_TYPE,
        keyValue: AssetFilterValueKeys.ASSET_TYPE,
        string: true,
        suggestions: (): string[] => get(assetTypes),
        validate: (): true => true,
      });
    }

    matcherList.push(
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
    );

    // Only add chain matcher if assetType filter is not set
    if (!get(filters).assetType) {
      matcherList.push({
        description: t('assets.filter.chain'),
        key: AssetFilterKeys.EVM_CHAIN,
        keyValue: AssetFilterValueKeys.EVM_CHAIN,
        string: true,
        suggestions: (): string[] => [...get(allEvmChains).map(x => x.name), 'solana'],
        validate: (chain: string): boolean => !!chain,
      });
    }

    matcherList.push({
      description: t('assets.filter.address'),
      hint: t('assets.filter.address_hint'),
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => !!address,
    });

    return matcherList;
  });

  const OptionalString = z.string().optional();
  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [AssetFilterValueKeys.ADDRESS]: OptionalString,
    [AssetFilterValueKeys.ASSET_TYPE]: OptionalString,
    [AssetFilterValueKeys.EVM_CHAIN]: OptionalString,
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
