import type { Ref } from 'vue';
import type { TableId } from '@/modules/table/use-remember-table-sorting';
import type { LocationQuery } from '@/types/route';
import { isEmpty } from 'es-toolkit/compat';

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

  const router = useRouter();
  const persistedFiltersRaw = useLocalStorage<Record<string, LocationQuery>>('rotki.table_filters', {});

  /**
   * Restores persisted filter from localStorage on mount
   */
  const restorePersistedFilter = async (): Promise<void> => {
    const tableIdValue = get(tableId);

    if (!get(enabled))
      return;

    const savedFilter = get(persistedFiltersRaw)[tableIdValue];

    if (savedFilter && !isEmpty(savedFilter)) {
      // Update query params so applyRouteFilter can pick them up
      if (history === 'router') {
        await router.replace({ query: savedFilter });
      }
      else if (history === 'external') {
        set(query, savedFilter);
      }
    }
  };

  /**
   * Saves filter to localStorage when it changes
   */
  const savePersistedFilter = (query: LocationQuery): void => {
    const tableIdValue = get(tableId);

    if (!get(enabled))
      return;

    const current = get(persistedFiltersRaw);
    set(persistedFiltersRaw, {
      ...current,
      [tableIdValue]: query,
    });
  };

  return {
    restorePersistedFilter,
    savePersistedFilter,
  };
}
