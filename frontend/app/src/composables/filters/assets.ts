import { z } from 'zod';
import { useSupportedChains } from '@/composables/info/chains';
import { arrayify } from '@/utils/array';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';

enum AssetFilterKeys {
  IDENTIFIER = 'identifier',
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'chain',
  ADDRESS = 'address',
}

enum AssetFilterValueKeys {
  IDENTIFIER = 'identifiers',
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'evmChain',
  ADDRESS = 'address',
}

export type Matcher = SearchMatcher<AssetFilterKeys, AssetFilterValueKeys>;

export type Filters = MatchedKeyword<AssetFilterValueKeys>;

export function useAssetFilter(): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { allEvmChains } = useSupportedChains();
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('assets.filter.identifier'),
      hint: t('assets.filter.identifier_hint'),
      key: AssetFilterKeys.IDENTIFIER,
      keyValue: AssetFilterValueKeys.IDENTIFIER,
      multiple: true,
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => isEvmIdentifier(address),
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
    {
      description: t('assets.filter.chain'),
      key: AssetFilterKeys.EVM_CHAIN,
      keyValue: AssetFilterValueKeys.EVM_CHAIN,
      string: true,
      suggestions: (): string[] => get(allEvmChains).map(x => x.name),
      validate: (chain: string): boolean => !!chain,
    },
    {
      description: t('assets.filter.address'),
      hint: t('assets.filter.address_hint'),
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => isValidEthAddress(address),
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
