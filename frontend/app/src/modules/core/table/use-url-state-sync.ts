import type { TablePaginationData } from '@rotki/ui-library';
import type { MaybeRefOrGetter, Ref } from 'vue';
import type { Schema } from 'zod';
import type { SingleColumnSorting, Sorting } from '@/modules/core/table/pagination-filter-types';
import type { LocationQuery } from '@/modules/core/table/route';
import type { ChangeSource } from '@/modules/core/table/use-change-intent';
import { isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { isNavigationFailure } from 'vue-router';
import {
  applyPaginationDefaults,
  parseQueryHistory,
  parseQueryPagination,
} from '@/modules/core/table/pagination-filter-utils';
import { applySourceReads, mergeParams, type ParamSource } from '@/modules/core/table/param-sources';

/**
 * Where a table's URL-shaped state lives.
 *
 * - `route`: the browser URL, pushed via vue-router.
 * - `ref`: a caller-owned ref, for embedded tables that must not touch the URL.
 *   The ref is required by the type: the old `history: 'external'` let you pass the
 *   mode without one, which silently synced to a throwaway internal ref instead.
 * - `none`: no URL state at all. No route watcher, no serialization.
 */
export type UrlState =
  | { mode: 'route' }
  | { mode: 'ref'; query: Ref<LocationQuery> }
  | { mode: 'none' };

/**
 * The "main page vs embedded" idiom, said once: a table that owns its page syncs to
 * the browser URL, an embedded copy of the same table must not touch it. Replaces
 * the `mainPage ? { mode: 'route' } : { mode: 'none' }` ternary repeated at the call
 * sites. `urlState` is read once at setup, so evaluating the condition here matches
 * the existing (non-reactive) semantics.
 */
export function routeWhen(mainPage: MaybeRefOrGetter<boolean>): UrlState {
  return toValue(mainPage) ? { mode: 'route' } : { mode: 'none' };
}

interface UseUrlStateSyncOptions<TItem extends NonNullable<unknown>, TFilter> {
  /** Which channel the URL-shaped state lives in. */
  urlState: UrlState;
  /** Param sources that contribute to the query. */
  params: ParamSource[];
  /** The filter state, overwritten when the URL is applied. */
  filters: Ref<TFilter>;
  /** Deserializes the raw query into the filter shape. */
  routeFilterSchema?: Schema;
  /** The global page size, used when resetting to defaults. */
  itemsPerPage: Ref<number>;
  /** The raw page/limit state, overwritten when the URL is applied. */
  internalPagination: Ref<TablePaginationData>;
  /** The raw sorting state, overwritten when the URL is applied. */
  internalSorting: Ref<Sorting<TItem>>;
  /** The sorting to fall back to, and to compare against when serializing. */
  defaultSorting: () => Sorting<TItem>;
  /** Column used when neither the query nor the defaults name one. */
  fallbackColumn?: string;
  /** Gates the URL write; only a `user` intent earns one. */
  pendingIntent: Ref<ChangeSource>;
  /** Lets the route watcher recognize the echo of our own write. */
  pendingUrlSource: Ref<ChangeSource | undefined>;
  /** Rehydrates saved filters when navigating to an empty query. */
  restorePersistedFilter: () => Promise<void>;
  /** Drops the transient values captured from the previous navigation. */
  resetTransientValues: () => void;
  /** Records the transient key values this navigation arrived with. */
  captureTransientValues: (routeQuery: LocationQuery, getQuery: () => LocationQuery) => void;
}

interface UseUrlStateSyncReturn {
  /** Returns the parsed pagination and filter query params. */
  getQuery: () => LocationQuery;
  /** Writes the current state back to the URL, if a user action earned it. */
  writeUrlState: () => Promise<void>;
}

function getSortColumns<TItem extends NonNullable<unknown>>(sorting: SingleColumnSorting<TItem>): string[] {
  return sorting.column ? [sorting.column] : [];
}

/**
 * Serializes table state into the URL and deserializes it back on navigation.
 *
 * Installs the route watcher as a side effect, so the call site decides where in
 * the watcher registration order it lands.
 */
export function useUrlStateSync<TItem extends NonNullable<unknown>, TFilter>(
  options: UseUrlStateSyncOptions<TItem, TFilter>,
): UseUrlStateSyncReturn {
  const {
    captureTransientValues,
    defaultSorting,
    fallbackColumn,
    filters,
    internalPagination,
    internalSorting,
    itemsPerPage,
    params,
    pendingIntent,
    pendingUrlSource,
    resetTransientValues,
    restorePersistedFilter,
    routeFilterSchema,
    urlState,
  } = options;

  const router = useRouter();
  const route = useRoute();

  const syncsUrl = urlState.mode !== 'none';

  /** Reads the query this table syncs against, whichever channel it lives in. */
  function readUrlQuery(): LocationQuery {
    if (urlState.mode === 'route')
      return get(route).query;
    if (urlState.mode === 'ref')
      return get(urlState.query);
    return {};
  }

  /**
   * Triggered on route change and on component mount
   * sets the pagination and filters values from url state
   */
  const applyUrlState = (): void => {
    if (!syncsUrl)
      return;

    const routeQuery = readUrlQuery();

    if (isEmpty(routeQuery)) {
      // for empty query, we reset the filters, and pagination to defaults
      applySourceReads(params, routeQuery);
      set(filters, routeFilterSchema?.parse({}));
      set(internalPagination, applyPaginationDefaults(get(itemsPerPage)));
      set(internalSorting, defaultSorting());
      return;
    }

    applySourceReads(params, routeQuery);
    set(filters, routeFilterSchema?.parse(routeQuery));
    set(internalPagination, parseQueryPagination(routeQuery, get(internalPagination)));
    set(internalSorting, parseQueryHistory(routeQuery, defaultSorting(), fallbackColumn));
  };

  /**
   * Returns the parsed pagination and filter query params
   * @returns {LocationQuery}
   */
  const getQuery = (): LocationQuery => {
    const { limit, page } = get(internalPagination);
    const sorting = get(internalSorting);

    const sortParams = isEqual(sorting, defaultSorting())
      ? undefined
      : {
          sort: Array.isArray(sorting) ? sorting.map(item => item.column) : getSortColumns(sorting),
          sortOrder: Array.isArray(sorting) ? sorting.map(item => item.direction) : [sorting.direction],
        };

    return {
      limit: limit.toString(),
      ...(page > 1 ? { page: page.toString() } : {}),
      ...sortParams,
      ...mergeParams(params, 'url', get(filters) ?? {}),
    };
  };

  async function writeUrlState(): Promise<void> {
    if (!syncsUrl || get(pendingIntent) !== 'user')
      return;

    const routeQuery = getQuery();
    if (isEqual(get(route)?.query, routeQuery))
      return;

    if (urlState.mode === 'route') {
      // Tag the write so the route watcher recognizes its own echo instead of
      // re-deserializing state that is already correct. Only route writes produce
      // an echo; tagging in `ref` mode would leave the tag set until some unrelated
      // navigation misread itself as ours.
      set(pendingUrlSource, 'self');
      const failure = await router.push({ query: routeQuery });

      // A push that is aborted or redirected by a guard resolves with a
      // NavigationFailure instead of throwing, and fires no route change. The tag
      // would then survive until some later, genuine navigation consumed it and
      // wrongly skipped applying that route's state. Clear it ourselves.
      if (isNavigationFailure(failure))
        set(pendingUrlSource, undefined);
    }
    else if (urlState.mode === 'ref') {
      set(urlState.query, routeQuery);
    }

    set(pendingIntent, 'programmatic');
  }

  // `none` means no URL state at all, so no route watcher is installed.
  if (syncsUrl) {
    watchImmediate(route, async () => {
      // Consume the pending tag: a write we made arrives as 'self', anything else is
      // a real navigation.
      const source = get(pendingUrlSource) ?? 'route';
      set(pendingUrlSource, undefined);
      set(pendingIntent, source);

      const routeQuery = readUrlQuery();

      // Only restore persisted filter if route/query is empty (route filter takes precedence)
      if (isEmpty(routeQuery)) {
        resetTransientValues();
        set(pendingIntent, 'restore');
        await restorePersistedFilter();
      }

      if (source !== 'self')
        applyUrlState();

      /**
       * Capture transient key values after url state is applied, so the values
       * reflect the parsed/transformed format used by getQuery() (e.g., arrayified strings).
       * Only capture once per navigation (when navigationTransientValues is not yet set).
       */
      captureTransientValues(routeQuery, getQuery);
    });
  }

  return {
    getQuery,
    writeUrlState,
  };
}
