import type { TablePaginationData } from '@rotki/ui-library';
import type { Ref, WritableComputedRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { ChangeSource } from '@/modules/core/table/use-change-intent';
import { applyPaginationDefaults } from '@/modules/core/table/pagination-filter-utils';

interface UseTablePaginationReturn {
  /** The raw page/limit state, without the server-derived total. */
  internalPagination: Ref<TablePaginationData>;
  /** The table-facing model. Its `total` is derived from the fetched collection. */
  pagination: WritableComputedRef<TablePaginationData>;
  setPage: (page: number, source?: ChangeSource) => void;
}

/**
 * Owns the pagination state of a server table. The collection is needed because
 * the total row count only exists on the server response.
 */
export function useTablePagination<TItem>(
  itemsPerPage: Ref<number>,
  collection: Ref<Collection<TItem>>,
  markSource: (source: ChangeSource) => void,
  markUserIntent: () => void,
): UseTablePaginationReturn {
  const internalPagination = ref<TablePaginationData>(applyPaginationDefaults(get(itemsPerPage)));

  const pagination = computed<TablePaginationData>({
    get() {
      const { limit, page } = get(internalPagination);
      const { found: total, limit: entriesLimit } = get(collection);
      return {
        limit,
        page,
        total: entriesLimit > 0 && entriesLimit < total ? entriesLimit : total,
      };
    },
    set(pagination) {
      markUserIntent();
      const currentPagination = get(internalPagination);
      set(internalPagination, {
        ...currentPagination,
        limit: pagination?.limit ?? currentPagination.limit,
        page: pagination?.page ?? currentPagination.page,
      });
    },
  });

  /**
   * Updates pagination data for just the current page
   */
  const setPage = (page: number, source: ChangeSource = 'user'): void => {
    markSource(source);
    set(internalPagination, { ...get(internalPagination), page });
  };

  return {
    internalPagination,
    pagination,
    setPage,
  };
}
