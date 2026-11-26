import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/core/common/collection';
import type { PillParams } from '@/modules/core/table/param-refs';
import type { FieldDef, PillBarLabels } from '@/modules/core/table/pill/core/types';
import type { UseTableDataReturn } from '@/modules/core/table/use-table-data';
import type { TableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, ref, toValue, type WritableComputedRef } from 'vue';
import { type Filters, manualBalanceTagsParams } from '@/modules/accounts/manual-balances/manual-balance-filter-keys';
import { useManualBalanceFields } from '@/modules/accounts/manual-balances/use-manual-balance-fields';
import { useManualBalancesOrLiabilities } from '@/modules/balances/manual/use-manual-balances-or-liabilities';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import { useServerTable, useTableEmptyState } from '@/modules/core/table/use-server-table';

interface UseManualBalanceTableOptions {
  /** Which side of the ledger the table lists. */
  readonly type: MaybeRefOrGetter<'liabilities' | 'balances'>;
  /** Whether prices are refreshing; the page is refetched once a refresh settles. */
  readonly pricesLoading: MaybeRefOrGetter<boolean>;
}

interface UseManualBalanceTableReturn {
  /** The page of balances the table renders. */
  state: Ref<Collection<ManualBalanceWithPrice>>;
  /** The last fetch failure, rendered in place of the rows. */
  error: UseTableDataReturn<ManualBalanceWithPrice>['error'];
  /** True while a page is being fetched. */
  loading: Ref<boolean>;
  /** The pill-bar fields the table filters on. */
  fields: FieldDef[];
  /** The pill bar's own copy. */
  pillLabels: ComputedRef<PillBarLabels>;
  /** The active filters; bound with `v-model:matches`. */
  modelFilter: WritableComputedRef<Filters>;
  /** The pill bar's params, which carry the tags; bound with `v-model:params`. */
  modelPillParams: WritableComputedRef<PillParams>;
  /** The active sort. */
  sort: WritableComputedRef<DataTableSortData<ManualBalanceWithPrice>>;
  /** Current page and size. */
  pagination: WritableComputedRef<TablePaginationData>;
  /** The table's empty text, replaced by the last fetch failure. */
  emptyState: ComputedRef<TableEmptyState>;
  /** Whether a filter or a tag narrows the table. */
  filtered: ComputedRef<boolean>;
  /** Drops every filter and tag. */
  clearFilters: () => void;
  /** Narrows the table to a tag, the same as picking it in the filter bar. */
  filterByTag: (tag: string) => void;
}

/**
 * The manual balances table's query: the filters and tags, the server-side page, and the refetches
 * that keep the page current when the balances change or a price refresh settles.
 */
export function useManualBalanceTable(options: UseManualBalanceTableOptions): UseManualBalanceTableReturn {
  const { pricesLoading, type } = options;

  const tags = ref<string[]>([]);

  const { pillParams, source: tagsSource } = manualBalanceTagsParams(tags);

  const { dataSource, fetch, locations } = useManualBalancesOrLiabilities(type);

  const modelFilters = ref<Filters>({});
  const fields = useManualBalanceFields(locations, modelFilters);
  const pillLabels = usePillBarLabels();

  const {
    collection: state,
    error,
    filter: filters,
    isLoading: loading,
    pagination,
    refetch: fetchData,
    sort,
  } = useServerTable<
    ManualBalanceWithPrice,
    ManualBalanceRequestPayload,
    Filters
  >({
    fetch,
    fields,
    filters: modelFilters,
    params: [tagsSource],
    sort: {
      default: [
        {
          column: 'value',
          direction: 'desc',
        },
      ],
    },
    urlState: { mode: 'route' },
  });

  const emptyState = useTableEmptyState({ error });

  const filtered = computed<boolean>(() => get(tags).length > 0 || Object.values(get(filters)).some(value => value !== undefined && value !== ''));

  function clearFilters(): void {
    set(filters, {});
    set(tags, []);
  }

  /** A tag in a row narrows the table to that tag, the same as picking it in the filter bar. */
  function filterByTag(tag: string): void {
    if (!get(tags).includes(tag))
      set(tags, [...get(tags), tag]);
  }

  watchImmediate(dataSource, async (newBalances, oldBalances) => {
    if (isEqual(newBalances, oldBalances))
      return;

    await fetchData();
  });

  watchDebounced(
    () => toValue(pricesLoading),
    async (isLoading, wasLoading) => {
      if (!isLoading && wasLoading)
        await fetchData();
    },
    { debounce: 800, maxWait: 1000 },
  );

  return {
    clearFilters,
    emptyState,
    error,
    fields,
    filterByTag,
    filtered,
    loading,
    modelFilter: filters,
    modelPillParams: pillParams,
    pagination,
    pillLabels,
    sort,
    state,
  };
}
