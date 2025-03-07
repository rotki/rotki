import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import type { MaybeRef } from '@vueuse/core';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { CommaSeparatedStringSchema, RouterExpandedIdsSchema } from '@/types/route';
import { arrayify } from '@/utils/array';
import { z } from 'zod';

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

  const { chainIds, isEvm } = useAccountCategoryHelper(category);

  const filterableChains = computed(() => {
    const evm = get(isEvm);
    const ids = get(chainIds);
    if (!evm)
      return ids;
    return [
      ...ids,
      'looopring',
    ];
  });

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('common.address'),
      key: BlockchainAccountFilterKeys.ADDRESS,
      keyValue: BlockchainAccountFilterValueKeys.ADDRESS,
      string: true,
      suggestions: (): string[] => [],
      validate: (): true => true,
    },
    {
      description: t('common.chain'),
      key: BlockchainAccountFilterKeys.CHAIN,
      keyValue: BlockchainAccountFilterValueKeys.CHAIN,
      multiple: true,
      string: true,
      suggestions: (): string[] => get(filterableChains),
      validate: (id: string): boolean => get(filterableChains).some(chainId => chainId.toLocaleLowerCase() === id.toLocaleLowerCase()),
    },
    {
      description: t('common.label'),
      key: BlockchainAccountFilterKeys.LABEL,
      keyValue: BlockchainAccountFilterValueKeys.LABEL,
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
    filters,
    matchers,
    RouteFilterSchema,
  };
}

export const AccountExternalFilterSchema = z.object({
  q: z.string().optional(),
  tab: z.coerce.number().optional(),
  tags: CommaSeparatedStringSchema,
}).merge(RouterExpandedIdsSchema);
