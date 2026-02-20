import type { Ref } from 'vue';
import type { TableId } from '@/modules/table/use-remember-table-sorting';
import type { LocationQuery } from '@/types/route';
import { objectOmit } from '@vueuse/shared';
import { isEmpty } from 'es-toolkit/compat';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';

interface UseRememberTableFilterOptions {
  enabled: Ref<boolean>;
  tableId: Ref<TableId>;
  query: Ref<LocationQuery>;
  history: false | 'router' | 'external';
}

interface UseRememberTableFilterReturn {
  restorePersistedFilter: () => Promise<void>;
  savePersistedFilter: (query: LocationQuery) => void;
}

export function useRememberTableFilter(
  options: UseRememberTableFilterOptions,
): UseRememberTableFilterReturn {
  const {
    enabled,
    history,
    query,
    tableId,
  } = options;

  const userId = useLoggedUserIdentifier();

  const router = useRouter();
  const persistedFiltersRaw = useLocalStorage<Record<string, LocationQuery>>(`${get(userId)}.rotki.table_filters`, {});

  /**
   * Restores persisted filter from localStorage on mount
   */
  const restorePersistedFilter = async (): Promise<void> => {
    const tableIdValue = get(tableId);

    if (!get(enabled))
      return;

    const savedFilter = get(persistedFiltersRaw)[tableIdValue];

    if (savedFilter && !isEmpty(savedFilter)) {
      // Strip page and limit — page resets to 1, limit comes from global itemsPerPage setting
      const filterWithoutPagination = objectOmit(savedFilter, ['page', 'limit']);

      // Update query params so applyRouteFilter can pick them up
      if (history === 'router') {
        await router.replace({ query: filterWithoutPagination });
      }
      else if (history === 'external') {
        set(query, filterWithoutPagination);
      }
    }
  };

  /**
   * Saves filter to localStorage when it changes
   * Always saves regardless of enabled state, so the latest filter is available when re-enabling
   */
  const savePersistedFilter = (query: LocationQuery): void => {
    const tableIdValue = get(tableId);

    const current = get(persistedFiltersRaw);
    set(persistedFiltersRaw, {
      ...current,
      // Strip limit — it should always come from global itemsPerPage setting
      [tableIdValue]: objectOmit(query, ['limit']),
    });
  };

  return {
    restorePersistedFilter,
    savePersistedFilter,
  };
}
