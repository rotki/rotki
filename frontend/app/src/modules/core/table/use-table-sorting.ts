import type { DataTableSortData } from '@rotki/ui-library';
import type { Ref, WritableComputedRef } from 'vue';
import type { Sorting } from '@/modules/core/table/pagination-filter-types';
import { applySortingDefaults, getSorting } from '@/modules/core/table/pagination-filter-utils';

interface UseTableSortingReturn<TItem extends NonNullable<unknown>> {
  /** The raw sorting state, in the shape the request payload and the URL need. */
  internalSorting: Ref<Sorting<TItem>>;
  /** The table-facing model. Writing to it is always a user action. */
  sort: WritableComputedRef<DataTableSortData<TItem>>;
  /** Recomputed on demand so the defaults are never shared between callers. */
  defaultSorting: () => Sorting<TItem>;
}

/**
 * Owns the sorting state of a server table.
 */
export function useTableSorting<TItem extends NonNullable<unknown>>(
  defaultSortBy: DataTableSortData<TItem> | undefined,
  markUserIntent: () => void,
  fallbackColumn?: string,
): UseTableSortingReturn<TItem> {
  const internalSorting = ref<Sorting<TItem>>(
    markRaw(applySortingDefaults(defaultSortBy, fallbackColumn)),
  ) as Ref<Sorting<TItem>>;

  const defaultSorting = (): Sorting<TItem> => applySortingDefaults(defaultSortBy, fallbackColumn);

  const sort = computed<DataTableSortData<TItem>>({
    get() {
      return get(internalSorting);
    },
    set(sort) {
      const defaults = defaultSorting();
      markUserIntent();
      let newSort = sort;
      if (newSort && defaults && !Array.isArray(newSort) && !Array.isArray(defaults)) {
        newSort = getSorting({
          column: newSort.column,
          direction: newSort.direction,
        }, defaults, fallbackColumn);
      }

      set(internalSorting, newSort);
    },
  });

  return {
    defaultSorting,
    internalSorting,
    sort,
  };
}
