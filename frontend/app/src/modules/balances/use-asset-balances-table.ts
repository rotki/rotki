import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBalancesDisplay } from '@/modules/balances/types/balances';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, ref, toRef, toValue } from 'vue';
import { useAssetBalanceSearch } from '@/modules/assets/use-asset-balance-search';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { useAssetBalancesHeaders } from '@/modules/balances/use-asset-balances-headers';
import { refDebounced } from '@/modules/core/common/async/scoped-timers';
import { bigNumberSum, calculatePercentage } from '@/modules/core/common/data/calculation';
import { sortAssetBalances } from '@/modules/core/common/display/balances';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseAssetBalancesTableOptions {
  /** The rows the table lists before any search narrows them. */
  readonly balances: MaybeRefOrGetter<AssetBalanceWithPrice[]>;
  /** The search text, matched against each row's asset once it settles. */
  readonly search: MaybeRefOrGetter<string>;
  /** Which optional columns to show. */
  readonly display: MaybeRefOrGetter<AssetBalancesDisplay | undefined>;
  /** Whether the table fills a panel, which fixes the column widths. */
  readonly fillsPanel: MaybeRefOrGetter<boolean>;
}

interface UseAssetBalancesTableReturn {
  debouncedSearch: Readonly<Ref<string>>;
  modelSort: Ref<DataTableSortData<AssetBalanceWithPrice>>;
  tableHeaders: ComputedRef<DataTableColumn<AssetBalanceWithPrice>[]>;
  matches: ComputedRef<AssetBalanceWithPrice[]>;
  sorted: ComputedRef<AssetBalanceWithPrice[]>;
  total: ComputedRef<BigNumber>;
  percentageOfTotalNetValue: (val: BigNumber) => string;
  percentageOfCurrentGroup: (val: BigNumber) => string;
}

/**
 * The rows of the asset balances table: searched, sorted with the remembered sorting, and totalled.
 */
export function useAssetBalancesTable(options: UseAssetBalancesTableOptions): UseAssetBalancesTableReturn {
  const { balances, display, fillsPanel, search } = options;

  const modelSort = ref<DataTableSortData<AssetBalanceWithPrice>>({
    column: 'value',
    direction: 'desc' as const,
  });

  const debouncedSearch = refDebounced(toRef(search), 200);

  const { getAssetInfo } = useAssetSelectInfo();
  const { matches, prioritizeExactMatches } = useAssetBalanceSearch(() => toValue(balances), debouncedSearch);
  const { totalNetWorth } = storeToRefs(useStatisticsStore());

  const total = computed<BigNumber>(() => bigNumberSum(get(matches).map(({ value }) => value)));

  function percentageOfTotalNetValue(val: BigNumber): string {
    return calculatePercentage(val, get(totalNetWorth));
  }

  function percentageOfCurrentGroup(val: BigNumber): string {
    return calculatePercentage(val, get(total));
  }

  const tableHeaders = useAssetBalancesHeaders(display, fillsPanel);

  useRememberTableSorting<AssetBalanceWithPrice>(TableId.ASSET_BALANCES, modelSort, tableHeaders);

  const sorted = computed<AssetBalanceWithPrice[]>(() =>
    prioritizeExactMatches(sortAssetBalances([...get(matches)], get(modelSort), getAssetInfo)));

  return {
    debouncedSearch,
    matches,
    modelSort,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    sorted,
    tableHeaders,
    total,
  };
}
