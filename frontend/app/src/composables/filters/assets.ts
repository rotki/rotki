import { z } from 'zod';
import type { MatchedKeyword, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

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
      key: AssetFilterKeys.SYMBOL,
      keyValue: AssetFilterValueKeys.SYMBOL,
      description: t('assets.filter.symbol'),
      hint: t('assets.filter.symbol_hint'),
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      key: AssetFilterKeys.NAME,
      keyValue: AssetFilterValueKeys.NAME,
      description: t('assets.filter.name'),
      hint: t('assets.filter.name_hint'),
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      key: AssetFilterKeys.EVM_CHAIN,
      keyValue: AssetFilterValueKeys.EVM_CHAIN,
      description: t('assets.filter.chain'),
      string: true,
      suggestions: (): string[] => get(allEvmChains).map(x => x.name),
      validate: (chain: string): boolean => !!chain,
    },
    {
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      description: t('assets.filter.address'),
      string: true,
      suggestions: (): string[] => [],
      validate: (address: string): boolean => isValidEthAddress(address),
    },
  ]);

  const OptionalString = z.string().optional();
  const RouteFilterSchema = z.object({
    [AssetFilterValueKeys.SYMBOL]: OptionalString,
    [AssetFilterValueKeys.NAME]: OptionalString,
    [AssetFilterValueKeys.EVM_CHAIN]: OptionalString,
    [AssetFilterValueKeys.ADDRESS]: OptionalString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
