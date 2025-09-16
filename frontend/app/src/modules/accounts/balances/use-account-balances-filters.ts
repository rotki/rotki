import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { ComponentExposed } from 'vue-component-type-helpers';
import type AccountGroupDetailsTable from '@/components/accounts/AccountGroupDetailsTable.vue';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { LocationQuery } from '@/types/route';
import { AccountExternalFilterSchema, type Filters, type Matcher, useBlockchainAccountFilter } from '@/composables/filters/blockchain-account';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { fromUriEncoded, toUriEncoded } from '@/utils/route-uri';

interface AccountBalancesFiltersReturn {
  accounts: Ref<Collection<BlockchainAccountGroupWithBalance>>;
  chainExclusionFilter: Ref<Record<string, string[]>>;
  detailsTable: Ref<ComponentExposed<typeof AccountGroupDetailsTable> | undefined>;
  expanded: Ref<string[]>;
  fetchData: () => Promise<void>;
  filters: WritableComputedRef<Filters>;
  matchers: ComputedRef<Matcher[]>;
  pagination: WritableComputedRef<TablePaginationData>;
  query: Ref<LocationQuery>;
  sort: WritableComputedRef<DataTableSortData<BlockchainAccountGroupWithBalance>>;
  tab: Ref<number>;
  visibleTags: Ref<string[]>;
}

export function useAccountBalancesFilters(category: MaybeRef<string>): AccountBalancesFiltersReturn {
  const { t } = useI18n();
  const { fetchAccounts: fetchAccountsPage } = useBlockchainAccountData();

  const visibleTags = ref<string[]>([]);
  const chainExclusionFilter = ref<Record<string, string[]>>({});
  const detailsTable = ref<ComponentExposed<typeof AccountGroupDetailsTable>>();
  const tab = ref<number>(0);
  const expanded = ref<string[]>([]);
  const query = ref<LocationQuery>({});

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
      column: 'usdValue',
      direction: 'desc',
    },
    extraParams: computed(() => ({
      category: get(category),
      tags: get(visibleTags),
    })),
    filterSchema: () => useBlockchainAccountFilter(t, category),
    history: 'router',
    onUpdateFilters(filterQuery) {
      const { expanded: expandedIds, q, tab: qTab, tags } = AccountExternalFilterSchema.parse(filterQuery);
      if (tags)
        set(visibleTags, tags);
      if (qTab !== undefined)
        set(tab, qTab);
      if (expandedIds)
        set(expanded, expandedIds);

      set(query, q ? fromUriEncoded(q) : {});
    },
    queryParamsOnly: computed(() => ({
      ...(get(expanded).length > 0
        ? {
            expanded: get(expanded),
            tab: get(tab),
            ...(get(tab) === 1
              ? {
                  q: toUriEncoded(get(query)),
                }
              : {}),
          }
        : {}),
    })),
    requestParams: computed(() => ({
      excluded: get(chainExclusionFilter),
    })),
  });

  return {
    accounts,
    chainExclusionFilter,
    detailsTable,
    expanded,
    fetchData,
    filters,
    matchers,
    pagination,
    query,
    sort,
    tab,
    visibleTags,
  };
}
