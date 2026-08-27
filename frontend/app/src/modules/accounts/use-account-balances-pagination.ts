import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import type { LocationQuery, RawLocationQuery } from '@/modules/core/table/route';
import { AccountExternalFilterSchema } from '@/modules/accounts/account-route-schema';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { fromUriEncoded, toUriEncoded } from '@/modules/core/common/helpers/route-uri';
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
   * Per-group chain exclusions keyed by group id, forwarded as the `excluded` request param. Read only,
   * this composable never writes it.
   */
  chainExclusionFilter: Ref<Record<string, string[]>>;
  /**
   * Active tab of the expanded row content. Mirrored into the URL only while at least one row is
   * expanded, and restored from the route on navigation.
   */
  tab: Ref<number>;
  /**
   * Group ids of the currently expanded rows. Drives whether any expansion state is put in the URL at
   * all: an empty array keeps the query clean.
   */
  expanded: Ref<string[]>;
  /**
   * Filter query of the nested table inside the expanded row. Persisted in the URL as a URI-encoded `q`
   * param for tab 1 only, and reset to `{}` when the route has no `q`.
   */
  query: Ref<LocationQuery>;
}

interface UseAccountBalancesPaginationReturn {
  accounts: Ref<Collection<BlockchainAccountGroupWithBalance>>;
  fetchData: () => Promise<void>;
  pagination: WritableComputedRef<TablePaginationData>;
  sort: WritableComputedRef<DataTableSortData<BlockchainAccountGroupWithBalance>>;
}

type QueryParams = Record<string, string | string[] | number>;

export function useAccountBalancesPagination(
  options: UseAccountBalancesPaginationOptions,
): UseAccountBalancesPaginationReturn {
  const {
    addresses,
    category,
    chains,
    chainExclusionFilter,
    expanded,
    query,
    tab,
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

  const queryParamsOnly = computed<QueryParams>(() => {
    const expandedIds = get(expanded);
    if (expandedIds.length === 0)
      return {};

    const currentTab = get(tab);
    return {
      expanded: expandedIds,
      tab: currentTab,
      ...(currentTab === 1 ? { q: toUriEncoded(get(query)) } : {}),
    };
  });

  const requestParams = computed<Record<string, unknown>>(() => ({
    excluded: get(chainExclusionFilter),
  }));

  function onUpdateFilters(filterQuery: LocationQuery): void {
    const { addresses: queryAddresses, chain, expanded: expandedIds, q, tab: qTab, tags } = AccountExternalFilterSchema.parse(filterQuery);

    if (tags)
      set(visibleTags, tags);

    if (queryAddresses)
      set(addresses, queryAddresses);

    const chainsInThisCategory = chain.filter(id => get(chainIds).includes(id));
    set(chains, chainsInThisCategory);

    if (qTab !== undefined)
      set(tab, qTab);

    if (expandedIds)
      set(expanded, expandedIds);

    set(query, q ? fromUriEncoded(q) : {});
  }

  const {
    collection: accounts,
    pagination,
    refetch: fetchData,
    sort,
  } = useServerTable<
    BlockchainAccountGroupWithBalance,
    BlockchainAccountRequestPayload
  >({
    fetch: fetchAccountsPage,
    params: [
      { to: 'both', values: extraParams },
      { skipEmpty: true, to: 'request', values: requestParams },
      { fromQuery: onUpdateFilters, skipEmpty: true, to: 'url', values: queryParamsOnly },
    ],
    sort: {
      default: {
        column: 'value',
        direction: 'desc',
      },
    },
    urlState: { mode: 'route' },
  });

  return {
    accounts,
    fetchData,
    pagination,
    sort,
  };
}
