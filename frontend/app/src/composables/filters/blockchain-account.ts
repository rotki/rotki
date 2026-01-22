import type { MaybeRef } from 'vue';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import { z } from 'zod/v4';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { CommaSeparatedStringSchema, RouterExpandedIdsSchema } from '@/types/route';
import { arrayify } from '@/utils/array';
import { getAccountAddress, getAccountLabel, getChain } from '@/utils/blockchain/accounts/utils';

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

export function useBlockchainAccountFilter(t: ReturnType<typeof useI18n>['t'], category: MaybeRef<string>): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { chainIds, isEvm } = useAccountCategoryHelper(category);
  const { addressNameSelector } = useAddressesNamesStore();

  const filterableChains = computed(() => {
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

  const matchers = computed<Matcher[]>(() => {
    const accounts = get(getAccountsByCategory(category));
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
            const label = item.data.type === 'xpub' ? getAccountLabel(item) : get(addressNameSelector(address, chain));

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
