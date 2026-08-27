import type { LocationQuery } from '@/modules/core/table/route';
import type { TableId } from '@/modules/core/table/use-remember-table-sorting';
import type { UrlState } from '@/modules/core/table/use-url-state-sync';
import { isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { useRememberTableFilter } from '@/modules/core/table/use-remember-table-filter';

/**
 * How a single query key is treated when persisting.
 *
 * - `never`: never persisted, regardless of how it was set.
 * - `untilChanged`: stripped only while the value still matches what the
 *   navigation arrived with. Once the user edits it, it persists.
 */
type PersistKeyPolicy = 'never' | 'untilChanged';

export interface PersistFilterSetting {
  tableId: TableId;
  /** Per-key overrides. Keys absent from the map are persisted normally. */
  keys?: Record<string, PersistKeyPolicy>;
}

interface UseTablePersistenceReturn {
  restorePersistedFilter: () => Promise<void>;
  savePersistedFilter: (query: LocationQuery) => void;
  /** Drops the transient values captured from the last navigation. */
  resetTransientValues: () => void;
  captureTransientValues: (routeQuery: LocationQuery, getQuery: () => LocationQuery) => void;
  /** Strips the excluded and still-untouched transient keys before persisting. */
  filterPersistedQuery: (query: LocationQuery) => LocationQuery;
}

/** The keys carrying a given policy, in declaration order. */
function keysWithPolicy(persist: PersistFilterSetting | undefined, policy: PersistKeyPolicy): string[] {
  return Object.entries(persist?.keys ?? {})
    .filter(([, value]) => value === policy)
    .map(([key]) => key);
}

/**
 * Owns which parts of a table's query survive into persisted filters.
 *
 * `persist` being absent means persistence is off; there is no separate `enabled`
 * flag to disagree with it.
 */
export function useTablePersistence(
  urlState: UrlState,
  persist?: PersistFilterSetting,
): UseTablePersistenceReturn {
  /** The persistence layer still speaks the old vocabulary; translate once. */
  const persistHistoryMode = ((): false | 'router' | 'external' => {
    if (urlState.mode === 'route')
      return 'router';
    if (urlState.mode === 'ref')
      return 'external';
    return false;
  })();

  const excludeKeys = keysWithPolicy(persist, 'never');
  const transientKeys = keysWithPolicy(persist, 'untilChanged');

  const { restorePersistedFilter, savePersistedFilter } = useRememberTableFilter({
    enabled: ref<boolean>(!!persist),
    history: persistHistoryMode,
    query: urlState.mode === 'ref' ? urlState.query : ref<LocationQuery>({}),
    tableId: ref<TableId | undefined>(persist?.tableId),
  });

  /**
   * The transient keys' values as an external navigation delivered them.
   *
   * @remarks
   * A key with the `untilChanged` policy is stripped from what gets persisted only while it still
   * holds the value the navigation brought. Once the user edits it, it becomes theirs and persists
   * like any other, which is what keeps a link-shared filter from being saved as a preference.
   */
  const navigationTransientValues = ref<Record<string, string | string[]>>();

  const resetTransientValues = (): void => {
    set(navigationTransientValues, undefined);
  };

  /**
   * Capture transient key values after url state is applied, so the values
   * reflect the parsed/transformed format used by getQuery() (e.g., arrayified strings).
   * Only capture once per navigation (when navigationTransientValues is not yet set).
   */
  const captureTransientValues = (routeQuery: LocationQuery, getQuery: () => LocationQuery): void => {
    if (isEmpty(routeQuery) || isDefined(navigationTransientValues))
      return;

    if (transientKeys.length === 0)
      return;

    const currentQuery = getQuery();
    const captured: Record<string, string | string[]> = {};
    for (const key of transientKeys) {
      // A query entry can be null or hold nulls; only the actual strings are worth capturing.
      const value = currentQuery[key];
      if (typeof value === 'string')
        captured[key] = value;
      else if (Array.isArray(value))
        captured[key] = value.filter(entry => entry !== null);
    }
    set(navigationTransientValues, Object.keys(captured).length > 0 ? captured : undefined);
  };

  const filterPersistedQuery = (query: LocationQuery): LocationQuery => {
    const keysToExclude = [...excludeKeys];

    // Only strip transient keys if their values haven't changed from the initial navigation values
    const navValues = get(navigationTransientValues);
    if (navValues) {
      for (const key of transientKeys) {
        if (key in navValues && isEqual(query[key], navValues[key]))
          keysToExclude.push(key);
      }
    }

    if (keysToExclude.length === 0)
      return query;

    const filteredQuery = { ...query };
    for (const key of keysToExclude)
      delete filteredQuery[key];

    return filteredQuery;
  };

  return {
    captureTransientValues,
    filterPersistedQuery,
    resetTransientValues,
    restorePersistedFilter,
    savePersistedFilter,
  };
}
