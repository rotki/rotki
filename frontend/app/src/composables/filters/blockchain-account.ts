import { z } from 'zod';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import type { FilterSchema } from '@/composables/filter-paginate';

enum BlockchainAccountFilterKeys {
  ADDRESS = 'address',
  CHAIN = 'chain',
  LABEL = 'label',
}

enum BlockchainAccountFilterValueKeys {
  ADDRESS = 'address',
  CHAIN = 'chain',
  LABEL = 'label',
}

export type Matcher = SearchMatcher<BlockchainAccountFilterKeys, BlockchainAccountFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<BlockchainAccountFilterValueKeys>;

export function useBlockchainAccountFilter(t: ReturnType<typeof useI18n>['t']): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { supportedChains } = useSupportedChains();

  const chainIds = useArrayMap(supportedChains, chain => chain.id);

  const matchers = computed<Matcher[]>(() => [
    {
      key: BlockchainAccountFilterKeys.ADDRESS,
      keyValue: BlockchainAccountFilterValueKeys.ADDRESS,
      description: t('common.address'),
      string: true,
      suggestions: () => [],
      validate: () => true,
    },
    {
      key: BlockchainAccountFilterKeys.CHAIN,
      keyValue: BlockchainAccountFilterValueKeys.CHAIN,
      description: t('common.chain'),
      string: true,
      suggestions: () => get(chainIds),
      validate: (id: string) => get(chainIds).some(chainId => chainId.toLocaleLowerCase() === id.toLocaleLowerCase()),
    },
    {
      key: BlockchainAccountFilterKeys.LABEL,
      keyValue: BlockchainAccountFilterValueKeys.LABEL,
      description: t('common.label'),
      string: true,
      suggestions: () => [],
      validate: () => true,
    },
  ]);

  const RouteFilterSchema = z.object({
    [BlockchainAccountFilterValueKeys.ADDRESS]: z.string().optional(),
    [BlockchainAccountFilterValueKeys.CHAIN]: z.string().optional(),
    [BlockchainAccountFilterValueKeys.LABEL]: z.string().optional(),
  });

  return {
    matchers,
    filters,
    RouteFilterSchema,
  };
}

export const AccountExternalFilterSchema = z.object({
  tags: z
    .string()
    .optional()
    .transform(val => (val ? val.split(',') : [])),
});
