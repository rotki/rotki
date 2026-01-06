import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { LocationQuery, RawLocationQuery } from '@/types/route';
import {
  AccountExternalFilterSchema,
  type Filters,
  getAccountFilterParams,
  type Matcher,
  useBlockchainAccountFilter,
} from '@/composables/filters/blockchain-account';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { fromUriEncoded, toUriEncoded } from '@/utils/route-uri';

interface UseAccountBalancesPaginationOptions {
  category: Ref<string>;
  visibleTags: Ref<string[]>;
  chainExclusionFilter: Ref<Record<string, string[]>>;
  tab: Ref<number>;
  expanded: Ref<string[]>;
  query: Ref<LocationQuery>;
}

interface UseAccountBalancesPaginationReturn {
  accounts: Ref<Collection<BlockchainAccountGroupWithBalance>>;
  fetchData: () => Promise<void>;
  filters: WritableComputedRef<Filters>;
  matchers: ComputedRef<Matcher[]>;
  pagination: WritableComputedRef<TablePaginationData>;
  sort: WritableComputedRef<DataTableSortData<BlockchainAccountGroupWithBalance>>;
}

interface RequestParams { excluded: Record<string, string[]>; address?: string; label?: string }

type QueryParams = Record<string, string | string[] | number>;

export function useAccountBalancesPagination(
  options: UseAccountBalancesPaginationOptions,
): UseAccountBalancesPaginationReturn {
  const { t } = useI18n({ useScope: 'global' });

  const {
    category,
    chainExclusionFilter,
    expanded,
    query,
    tab,
    visibleTags,
  } = options;

  const { fetchAccounts: fetchAccountsPage } = useBlockchainAccountData();
  const filterSchema = useBlockchainAccountFilter(t, category);

  const extraParams = computed<RawLocationQuery>(() => ({
    category: get(category),
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

  const requestParams = computed<RequestParams>(() => ({
    excluded: get(chainExclusionFilter),
    ...getAccountFilterParams(get(filterSchema.filters).account),
  }));

  function onUpdateFilters(filterQuery: LocationQuery): void {
    const { expanded: expandedIds, q, tab: qTab, tags } = AccountExternalFilterSchema.parse(filterQuery);

    if (tags)
      set(visibleTags, tags);

    if (qTab !== undefined)
      set(tab, qTab);

    if (expandedIds)
      set(expanded, expandedIds);

    set(query, q ? fromUriEncoded(q) : {});
  }

  const {
    fetchData,
    filters,
    matchers,
    pagination,
    sort,
    state: accounts,
  } = usePaginationFilters<
    BlockchainAccountGroupWithBalance,
    BlockchainAccountRequestPayload,
    Filters,
    Matcher
  >(fetchAccountsPage, {
    defaultSortBy: {
      column: 'value',
      direction: 'desc',
    },
    extraParams,
    filterSchema: () => filterSchema,
    history: 'router',
    onUpdateFilters,
    queryParamsOnly,
    requestParams,
  });

  return {
    accounts,
    fetchData,
    filters,
    matchers,
    pagination,
    sort,
  };
}
