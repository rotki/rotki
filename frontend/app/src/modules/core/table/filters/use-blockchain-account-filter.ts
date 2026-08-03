import type { MaybeRefOrGetter } from 'vue';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { arrayify } from '@/modules/core/common/data/array';
import { CommaSeparatedStringSchema, RouterExpandedIdsSchema } from '@/modules/core/table/route';

enum BlockchainAccountFilterKeys {
  CHAIN = 'chain',
}

enum BlockchainAccountFilterValueKeys {
  CHAIN = 'chain',
}

export type Matcher = SearchMatcher<BlockchainAccountFilterKeys, BlockchainAccountFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<BlockchainAccountFilterValueKeys>;

export function useBlockchainAccountFilter(t: ReturnType<typeof useI18n>['t'], category: MaybeRefOrGetter<string>): FilterSchema<Filters, Matcher> {
  const modelFilters = ref<Filters>({});

  const { chainIds } = useAccountCategoryHelper(category);

  const filterableChains = computed<string[]>(() => get(chainIds));

  const matchers = computed<Matcher[]>(() => [
    {
      description: t('account_balances.filter.chain'),
      key: BlockchainAccountFilterKeys.CHAIN,
      keyValue: BlockchainAccountFilterValueKeys.CHAIN,
      multiple: true,
      string: true,
      suggestions: (): string[] => get(filterableChains),
      validate: (id: string): boolean => get(filterableChains).some(chainId => chainId.toLocaleLowerCase() === id.toLocaleLowerCase()),
    },
  ]);

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [BlockchainAccountFilterValueKeys.CHAIN]: OptionalMultipleString,
  });

  return {
    filters: modelFilters,
    matchers,
    RouteFilterSchema,
  };
}

export const AccountExternalFilterSchema = z.object({
  addresses: CommaSeparatedStringSchema,
  q: z.string().optional(),
  tab: z.coerce.number().optional(),
  tags: CommaSeparatedStringSchema,
  ...RouterExpandedIdsSchema.shape,
});
