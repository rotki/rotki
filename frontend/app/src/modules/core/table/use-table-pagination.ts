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
 *
 * Writes go through `commitPage`/`commitLimit`, which dispatch `page-set`/`limit-set`
 * events; the reducer decides the transition (including whether a change resets the
 * page) and the adapter writes `internalPagination` back. This composable no longer
 * mutates it directly.
 */
export function useTablePagination<TItem>(
  itemsPerPage: Ref<number>,
  collection: Ref<Collection<TItem>>,
  commitPage: (page: number, source?: ChangeSource) => void,
  commitLimit: (limit: number) => void,
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
      const current = get(internalPagination);
      const limit = pagination?.limit ?? current.limit;
      const page = pagination?.page ?? current.page;
      // Emit only what actually changed; each is a user-driven change.
      if (limit !== current.limit)
        commitLimit(limit);
      if (page !== current.page)
        commitPage(page);
    },
  });

  /**
   * Updates pagination data for just the current page
   */
  const setPage = (page: number, source: ChangeSource = 'user'): void => {
    commitPage(page, source);
  };

  return {
    internalPagination,
    pagination,
    setPage,
  };
}
