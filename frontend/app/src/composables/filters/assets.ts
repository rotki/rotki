import { type ComputedRef, type Ref } from 'vue';
import { type MatchedKeyword, type SearchMatcher } from '@/types/filtering';
import { isValidEthAddress } from '@/utils/text';

enum AssetFilterKeys {
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'chain',
  ADDRESS = 'address'
}

enum AssetFilterValueKeys {
  SYMBOL = 'symbol',
  NAME = 'name',
  EVM_CHAIN = 'evmChain',
  ADDRESS = 'address'
}

type Matcher = SearchMatcher<AssetFilterKeys, AssetFilterValueKeys>;
type Filters = MatchedKeyword<AssetFilterValueKeys>;

export const useAssetFilter = () => {
  const filters: Ref<Filters> = ref({});

  const { allEvmChains } = useSupportedChains();
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => [
    {
      key: AssetFilterKeys.SYMBOL,
      keyValue: AssetFilterValueKeys.SYMBOL,
      description: tc('assets.filter.symbol'),
      hint: tc('assets.filter.symbol_hint'),
      string: true,
      suggestions: () => [],
      validate: () => true
    },
    {
      key: AssetFilterKeys.NAME,
      keyValue: AssetFilterValueKeys.NAME,
      description: tc('assets.filter.name'),
      hint: tc('assets.filter.name_hint'),
      string: true,
      suggestions: () => [],
      validate: () => true
    },
    {
      key: AssetFilterKeys.EVM_CHAIN,
      keyValue: AssetFilterValueKeys.EVM_CHAIN,
      description: tc('assets.filter.chain'),
      string: true,
      suggestions: () => get(allEvmChains).map(x => x.name),
      validate: (chain: string) => !!chain
    },
    {
      key: AssetFilterKeys.ADDRESS,
      keyValue: AssetFilterValueKeys.ADDRESS,
      description: tc('assets.filter.address'),
      string: true,
      suggestions: () => [],
      validate: (address: string) => isValidEthAddress(address)
    }
  ]);

  const updateFilter = (newFilters: Filters) => {
    set(filters, newFilters);
  };

  return {
    filters,
    matchers,
    updateFilter
  };
};
