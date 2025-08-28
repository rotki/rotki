import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { getCollectionData } from '@/utils/collection';

interface UseNftDataReturn {
  balances: Ref<Collection<NonFungibleBalance>>;
  currencySymbol: ComputedRef<string>;
  data: ComputedRef<NonFungibleBalance[]>;
  dataLoading: Ref<boolean>;
  fetchData: () => Promise<void>;
  ignoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
  pagination: ComputedRef<TablePaginationData>;
  refreshNonFungibleBalances: (ignoreCache?: boolean) => Promise<void>;
  sectionLoading: ComputedRef<boolean>;
  sort: ComputedRef<DataTableSortData<NonFungibleBalance>>;
  cols: ComputedRef<DataTableColumn<NonFungibleBalance>[]>;
  totalUsdValue: ComputedRef<BigNumber | undefined | null>;
}

export function useNftData(): UseNftDataReturn {
  const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNftBalances();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { t } = useI18n({ useScope: 'global' });

  const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

  const extraParams = computed(() => ({
    ignoredAssetsHandling: get(ignoredAssetsHandling),
  }));

  const cols = computed<DataTableColumn<NonFungibleBalance>[]>(() => [{
    cellClass: 'text-no-wrap',
    key: 'name',
    label: t('common.name'),
    sortable: true,
  }, {
    align: 'center',
    key: 'ignored',
    label: t('non_fungible_balances.ignore'),
  }, {
    align: 'end',
    class: 'text-no-wrap',
    key: 'priceInAsset',
    label: t('non_fungible_balances.column.price_in_asset'),
    width: '75%',
  }, {
    align: 'end',
    class: 'text-no-wrap',
    key: 'usdPrice',
    label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  }, {
    class: 'text-no-wrap',
    key: 'manuallyInput',
    label: t('non_fungible_balances.column.custom_price'),
  }, {
    align: 'center',
    key: 'actions',
    label: t('common.actions_text'),
    width: '50',
  }]);

  const { isLoading: isSectionLoading } = useStatusStore();
  const sectionLoading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

  const {
    fetchData,
    isLoading: dataLoading,
    pagination,
    setPage,
    sort,
    state: balances,
  } = usePaginationFilters<
    NonFungibleBalance,
    NonFungibleBalancesRequestPayload
  >(fetchNonFungibleBalances, {
    defaultSortBy: [{
      column: 'usdPrice',
      direction: 'desc',
    }],
    extraParams,
    history: 'router',
    onUpdateFilters(query) {
      set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
    },
  });

  useRememberTableSorting<NonFungibleBalance>(TableId.NON_FUNGIBLE_BALANCES, sort, cols);

  // Extract collection data
  const { data, totalUsdValue } = getCollectionData(balances);

  // Watch ignoredAssetsHandling changes and reset to page 1
  watch(ignoredAssetsHandling, () => {
    setPage(1);
  });

  return {
    balances,
    cols,
    currencySymbol,
    data,
    dataLoading,
    fetchData,
    ignoredAssetsHandling,
    pagination,
    refreshNonFungibleBalances,
    sectionLoading,
    sort,
    totalUsdValue,
  };
}
