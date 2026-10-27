import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import type { LocationQuery, RawLocationQuery } from '@/modules/core/table/route';
import { AccountExternalFilterSchema } from '@/modules/accounts/account-route-schema';
import { ACCOUNT_DETAILS_QUERY_KEYS } from '@/modules/accounts/details/use-account-details-route';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useServerTable } from '@/modules/core/table/use-server-table';

interface UseAccountBalancesPaginationOptions {
  /**
   * Account category the page is showing (`evm`, `solana`, ...). It decides which chains the chain
   * pill offers and is sent as a request param, so changing it refetches.
   */
  category: MaybeRefOrGetter<string>;
  /**
   * Tags picked in the filter bar, sent as the `tags` request param. Written back by this composable
   * when the route carries tags, so it is two-way: the caller owns the ref, the URL can overwrite it.
   */
  visibleTags: Ref<string[]>;
  /**
   * Accounts picked in the filter bar, sent as the `addresses` request param and mirrored in the
   * URL. Written back by this composable when the route carries addresses, like `visibleTags`.
   */
  addresses: Ref<string[]>;
  /**
   * Chains picked in the filter bar, sent as the `chain` request param and mirrored in the URL.
   * Written back by this composable when the route carries chains, like `visibleTags`.
   */
  chains: Ref<string[]>;
  /**
   * Per-group chain exclusions keyed by group id, passed as `excluded` to the local account filter.
   * Read only, this composable never writes it.
   */
  chainExclusionFilter: Ref<Record<string, string[]>>;
}

interface UseAccountBalancesPaginationReturn {
  accounts: Ref<Collection<BlockchainAccountGroupWithBalance>>;
  fetchData: () => Promise<void>;
  /** A page fetch is in flight; before the first one lands, an empty list means "not loaded yet". */
  isLoading: Ref<boolean>;
  pagination: WritableComputedRef<TablePaginationData>;
  sort: WritableComputedRef<DataTableSortData<BlockchainAccountGroupWithBalance>>;
}

export function useAccountBalancesPagination(
  options: UseAccountBalancesPaginationOptions,
): UseAccountBalancesPaginationReturn {
  const {
    addresses,
    category,
    chains,
    chainExclusionFilter,
    visibleTags,
  } = options;

  const { fetchAccounts: fetchAccountsPage } = useBlockchainAccountData();
  const { chainIds } = useAccountCategoryHelper(category);

  const extraParams = computed<RawLocationQuery>(() => ({
    addresses: get(addresses),
    category: toValue(category),
    chain: get(chains),
    tags: get(visibleTags),
  }));

  const requestParams = computed<Record<string, unknown>>(() => ({
    excluded: get(chainExclusionFilter),
  }));

  function onUpdateFilters(filterQuery: LocationQuery): void {
    const { addresses: queryAddresses, chain, tags } = AccountExternalFilterSchema.parse(filterQuery);

    if (tags)
      set(visibleTags, tags);

    if (queryAddresses)
      set(addresses, queryAddresses);

    const chainsInThisCategory = chain.filter(id => get(chainIds).includes(id));
    set(chains, chainsInThisCategory);
  }

  const {
    collection: accounts,
    isLoading,
    pagination,
    refetch: fetchData,
    sort,
  } = useServerTable<
    BlockchainAccountGroupWithBalance,
    BlockchainAccountRequestPayload
  >({
    fetch: fetchAccountsPage,
    params: [
      { fromQuery: onUpdateFilters, to: 'both', values: extraParams },
      { skipEmpty: true, to: 'request', values: requestParams },
    ],
    sort: {
      default: {
        column: 'value',
        direction: 'desc',
      },
    },
    urlState: { keep: ACCOUNT_DETAILS_QUERY_KEYS, mode: 'route' },
  });

  return {
    accounts,
    fetchData,
    isLoading,
    pagination,
    sort,
  };
}
