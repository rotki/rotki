import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import { useSupportedChains } from '@/composables/info/chains';
import { z } from 'zod';

enum AssetFilterKeys {
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'chain',
  ADDRESS = 'address',
}

enum AssetFilterValueKeys {
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
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => isValidEthAddress(address),
    },
  ]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AssetFilterValueKeys.ADDRESS]: OptionalString,
    [AssetFilterValueKeys.EVM_CHAIN]: OptionalString,
    [AssetFilterValueKeys.NAME]: OptionalString,
    [AssetFilterValueKeys.SYMBOL]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
