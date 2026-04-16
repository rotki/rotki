import type { MaybeRefOrGetter } from 'vue';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { z } from 'zod/v4';
import { getAccountAddress, getAccountLabel, getChain, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { arrayify } from '@/modules/core/common/data/array';
import { CommaSeparatedStringSchema, RouterExpandedIdsSchema } from '@/modules/core/table/route';

enum BlockchainAccountFilterKeys {
  ACCOUNT = 'account',
  CHAIN = 'chain',
}

enum BlockchainAccountFilterValueKeys {
  ACCOUNT = 'account',
  CHAIN = 'chain',
}

export type Matcher = SearchMatcher<BlockchainAccountFilterKeys, BlockchainAccountFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<BlockchainAccountFilterValueKeys>;

export function useBlockchainAccountFilter(t: ReturnType<typeof useI18n>['t'], category: MaybeRefOrGetter<string>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { chainIds, isEvm } = useAccountCategoryHelper(category);
  const { getAddressName } = useAddressNameResolution();

  const filterableChains = computed<string[]>(() => {
    const evm = get(isEvm);
    const ids = get(chainIds);
    if (!evm)
      return ids;
    return [
      ...ids,
      'loopring',
    ];
  });

  const { getAccountsByCategory } = useBlockchainAccountData();
  const accountsByCategory = getAccountsByCategory(category);

  const matchers = computed<Matcher[]>(() => {
    const accounts = get(accountsByCategory);
    return [
      {
        description: t('account_balances.filter.account'),
        key: BlockchainAccountFilterKeys.ACCOUNT,
        keyValue: BlockchainAccountFilterValueKeys.ACCOUNT,
        strictMatching: true,
        string: true,
        suggestions: (): string[] => {
          const suggestions: string[] = [];
          const seenAddresses = new Set<string>();

          for (const item of accounts) {
            const address = getAccountAddress(item);
            const chain = getChain(item);
            const label = isXpubAccount(item) ? getAccountLabel(item) : getAddressName(address, chain);

            if (!seenAddresses.has(address)) {
              seenAddresses.add(address);
              // If account has a distinct label, show "label (address)", otherwise just address
              if (label && label !== address)
                suggestions.push(`${label} (${address})`);
              else
                suggestions.push(address);
            }
          }

          return suggestions;
        },
        validate: (): true => true,
      },
      {
        description: t('account_balances.filter.chain'),
        key: BlockchainAccountFilterKeys.CHAIN,
        keyValue: BlockchainAccountFilterValueKeys.CHAIN,
        multiple: true,
        string: true,
        suggestions: (): string[] => get(filterableChains),
        validate: (id: string): boolean => get(filterableChains).some(chainId => chainId.toLocaleLowerCase() === id.toLocaleLowerCase()),
      },
    ];
  });

  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [BlockchainAccountFilterValueKeys.ACCOUNT]: z.string().optional(),
    [BlockchainAccountFilterValueKeys.CHAIN]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}

/**
 * Extracts address and label from unified account filter value.
 * Handles both "label (address)" format and plain address/label strings.
 */
export function getAccountFilterParams(accountValue: Filters['account']): { address?: string; label?: string } {
  if (!accountValue || typeof accountValue !== 'string')
    return {};

  // Check if the value is in "label (address)" format
  const match = accountValue.match(/^(.+?)\s*\(([^)]+)\)$/);
  if (match) {
    // Format: "label (address)" - use address for filtering
    return { address: match[2], label: match[1] };
  }

  // Plain value - could be address or label, send to both
  return { address: accountValue, label: accountValue };
}

export const AccountExternalFilterSchema = z.object({
  q: z.string().optional(),
  tab: z.coerce.number().optional(),
  tags: CommaSeparatedStringSchema,
  ...RouterExpandedIdsSchema.shape,
});
