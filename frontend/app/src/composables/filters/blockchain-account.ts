import { z } from 'zod';
import type { MaybeRef } from '@vueuse/core';
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

export function useBlockchainAccountFilter(t: ReturnType<typeof useI18n>['t'], category: MaybeRef<string>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { supportedChains: allChains } = useSupportedChains();

  const chainIds = computed<string[]>(() => {
    const chains = get(allChains);
    const categoryVal = get(category);
    if (categoryVal === 'all')
      return chains.map(chain => chain.id);

    return chains.filter(item => item.type === categoryVal || (categoryVal === 'evm' && item.type === 'evmlike')).map(chain => chain.id);
  });

  const matchers = computed<Matcher[]>(() => [
    {
      key: BlockchainAccountFilterKeys.ADDRESS,
      keyValue: BlockchainAccountFilterValueKeys.ADDRESS,
      description: t('common.address'),
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      key: BlockchainAccountFilterKeys.CHAIN,
      keyValue: BlockchainAccountFilterValueKeys.CHAIN,
      description: t('common.chain'),
      multiple: true,
      string: true,
      suggestions: (): string[] => get(chainIds),
      validate: (id: string): boolean => get(chainIds).some(chainId => chainId.toLocaleLowerCase() === id.toLocaleLowerCase()),
    },
    {
      key: BlockchainAccountFilterKeys.LABEL,
      keyValue: BlockchainAccountFilterValueKeys.LABEL,
      description: t('common.label'),
      string: true,
      suggestions: (): string[] => [],
      validate: (): boolean => true,
    },
  ]);

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [BlockchainAccountFilterValueKeys.ADDRESS]: z.string().optional(),
    [BlockchainAccountFilterValueKeys.CHAIN]: OptionalMultipleString,
    [BlockchainAccountFilterValueKeys.LABEL]: z.string().optional(),
  });

  return {
    matchers,
    filters,
    RouteFilterSchema,
  };
}

export const AccountExternalFilterSchema = z.object({
  tags: z.string()
    .optional()
    .transform(val => (val ? val.split(',') : [])),
});
