import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type DeepReadonly, type MaybeRefOrGetter, type Ref, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTrackedAccountsRow } from '@/modules/accounts/use-tracked-accounts-row';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useValuePending } from '@/modules/balances/value-pending';
import { useDashboardAssetData } from '@/modules/dashboard/use-dashboard-asset-data';
import { useDashboardAssetOperations } from '@/modules/dashboard/use-dashboard-asset-operations';
import { useDashboardStores } from '@/modules/dashboard/use-dashboard-stores';
import { useDashboardTableConfig } from '@/modules/dashboard/use-dashboard-table-config';
import { fitsEveryLimit } from '@/modules/session/use-items-per-page';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';

interface UseDashboardAssetTableOptions {
  /** The rows the table lists, before search and sorting. */
  balances: MaybeRefOrGetter<AssetBalanceWithPrice[]>;
  /** Which dashboard table this is, for its visible columns, row expansion and empty text. */
  tableType: MaybeRefOrGetter<DashboardTableType>;
  /** The table's title, used in the current-group percentage header. */
  title: MaybeRefOrGetter<string>;
  /** Add the column the page fills through the `comparison` slot. */
  showComparison: MaybeRefOrGetter<boolean>;
}

interface UseDashboardAssetTableReturn {
  modelSort: Ref<DataTableSortData<AssetBalanceWithPrice>>;
  modelSearch: Ref<string>;
  modelExpanded: Ref<AssetBalanceWithPrice[]>;
  pagination: DeepReadonly<Ref<{ itemsPerPage: number; page: number }>>;
  setTablePagination: (event: TablePaginationData | undefined) => void;
  tableHeaders: ComputedRef<DataTableColumn<AssetBalanceWithPrice>[]>;
  sorted: ComputedRef<AssetBalanceWithPrice[]>;
  total: ComputedRef<BigNumber>;
  isAssetMissing: (item: AssetBalanceWithPrice) => boolean;
  percentageOfCurrentGroup: (item: AssetBalanceWithPrice) => string;
  percentageOfTotalNetValue: (item: AssetBalanceWithPrice) => string;
  isRowExpandable: (row: AssetBalanceWithPrice) => boolean;
  redirectToManualBalance: (item: AssetBalanceWithPrice) => void;
  isValuePending: (row: AssetBalanceWithPrice) => boolean;
  isPriceMissing: (asset: string) => boolean;
  placeholderRowClass: (row: AssetBalanceWithPrice) => string;
  emptyDescription: ComputedRef<string>;
  totalPending: ComputedRef<boolean>;
  searchable: ComputedRef<boolean>;
  hidePagination: ComputedRef<boolean>;
  showTotal: ComputedRef<boolean>;
}

/** Below this many rows the whole table is in view, so a search field only takes space. */
const SEARCH_MIN_ROWS = 11;

/**
 * Rows, columns, paging and display state of a dashboard asset table.
 *
 * @param options - getters for the table's props, so the table follows them after mounting
 */
export function useDashboardAssetTable(options: UseDashboardAssetTableOptions): UseDashboardAssetTableReturn {
  const { balances, showComparison, tableType, title } = options;
  const { t } = useI18n({ useScope: 'global' });

  const { totalNetWorth } = useDashboardStores();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { isTotalPending, isValuePending } = useValuePending();

  // Use composables - sort needs to be defined first for the computed dependency
  const { modelSort, pagination, setPage, setTablePagination, tableHeaders } = useDashboardTableConfig(
    tableType,
    title,
    totalNetWorth,
    showComparison,
  );

  const {
    isAssetMissing,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    modelSearch,
    sorted,
    total,
  } = useDashboardAssetData(balances, modelSort);

  const { isRowExpandable, modelExpanded, redirectToManualBalance } = useDashboardAssetOperations(tableType);

  const { raised: tracksNothing } = useTrackedAccountsRow();

  /**
   * The assets table's own text only while something is tracked.
   *
   * @remarks
   * With nothing tracked, the Assets by source card above already shows the tracked accounts row, so
   * the table stays neutral rather than saying it a second time.
   */
  const emptyDescription = computed<string>(() => toValue(tableType) === DashboardTableType.ASSETS && !get(tracksNothing)
    ? t('dashboard_asset_table.no_assets')
    : t('data_table.no_data'));

  /**
   * Mutes a placeholder row: an asset listed at zero because only the other balance view holds it.
   *
   * @remarks
   * Only placeholder rows have a zero amount, since aggregation drops held assets that sum to zero.
   */
  function placeholderRowClass(row: AssetBalanceWithPrice): string {
    return row.amount.isZero() ? 'opacity-60' : '';
  }

  function isPriceMissing(asset: string): boolean {
    return get(prices)[asset]?.priceMissing === true;
  }

  const totalPending = computed<boolean>(() => isTotalPending(get(sorted)));

  const searchable = computed<boolean>(() => toValue(balances).length >= SEARCH_MIN_ROWS);

  const hidePagination = computed<boolean>(() => fitsEveryLimit(get(sorted).length));

  /** With one row the row is its own total. */
  const showTotal = computed<boolean>(() => get(sorted).length > 1 && get(modelSearch).length === 0);

  watch(modelSearch, () => setPage(1));

  return {
    emptyDescription,
    hidePagination,
    isAssetMissing,
    isPriceMissing,
    isRowExpandable,
    isValuePending,
    modelExpanded,
    modelSearch,
    modelSort,
    pagination,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    placeholderRowClass,
    redirectToManualBalance,
    searchable,
    setTablePagination,
    showTotal,
    sorted,
    tableHeaders,
    total,
    totalPending,
  };
}
