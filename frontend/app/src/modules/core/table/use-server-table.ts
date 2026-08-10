import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { Schema } from 'zod';
import type { Collection } from '@/modules/core/common/collection';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { isEqual } from 'es-toolkit';
import { getApiSortingParams } from '@/modules/core/table/pagination-filter-utils';
import { collectSources, mergeParams, type ParamSource, transformFilters } from '@/modules/core/table/param-sources';
import { behaviourKeysFromFields, routeSchemaFromFields } from '@/modules/core/table/route';
import { type ChangeSource, useChangeIntent } from '@/modules/core/table/use-change-intent';
import { useTableData } from '@/modules/core/table/use-table-data';
import { useTablePagination } from '@/modules/core/table/use-table-pagination';
import { type PersistFilterSetting, useTablePersistence } from '@/modules/core/table/use-table-persistence';
import { reduce, type TableEvent, type TableState } from '@/modules/core/table/use-table-reducer';
import { useTableSorting } from '@/modules/core/table/use-table-sorting';
import { routeWhen, type UrlState, useUrlStateSync } from '@/modules/core/table/use-url-state-sync';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';

// Re-exported so the facade's public surface stays exactly what it was before the
// provenance and URL-sync internals moved into their own modules.
export type { ChangeSource };

export { routeWhen };

interface TableSortOptions<TItem extends NonNullable<unknown>> {
  /** The sorting a table starts at, and returns to when the URL carries none. */
  default?: DataTableSortData<TItem>;
  /**
   * Column used when neither the state nor `default` names one.
   * Defaults to `timestamp`, which every table used to be hardcoded to.
   */
  fallbackColumn?: string;
}

interface TableRequestOptions {
  /** Milliseconds to coalesce rapid payload changes into one fetch. `0` fetches on every change. */
  debounce?: number;
  /** Cancels in-flight requests carrying this tag before each fetch. */
  cancelTag?: string;
}

interface UseServerTableOptions<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem extends Array<infer U> ? U : TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
> {
  /** The request function. `TPayload` is inferred from its parameter. */
  fetch: (payload: MaybeRef<TPayload>) => Promise<Collection<TItem>>;
  /** URL query sync mode; defaults to `{ mode: 'none' }` (no URL binding). */
  urlState?: UrlState;
  /**
   * The filter schema itself, not a factory: the caller holds it, and the pill bar reads the same
   * filter bag. Named `filterSchema` because `filter` is the returned value.
   */
  filterSchema?: FilterSchema<TFilter>;
  /**
   * The pill-bar fields this table filters on, the same list the bar is given. The url shape of the
   * filter bag and the keys the request wraps as `{ behaviour, values }` are read off them, rather
   * than restated per table beside a field list that already says both.
   */
  fields?: MaybeRefOrGetter<FieldDef[]>;
  /** External parameter sources merged into the request payload and/or URL. */
  params?: ParamSource[];
  /** Default sort column and fallback column applied when none is persisted. */
  sort?: TableSortOptions<TItem>;
  /** Absent means no persistence at all. */
  persist?: PersistFilterSetting;
  /** Request-level behaviour: cancellation tag and fetch debounce. */
  request?: TableRequestOptions;
}

interface UseServerTableReturn<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem extends Array<infer U> ? U : TItem> = PaginationRequestPayload<TItem extends Array<infer U> ? U : TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
> {
  /** The assembled request payload. Forwarded by tables that lazily load sub-rows. */
  requestPayload: ComputedRef<TPayload>;
  isLoading: Ref<boolean>;
  /** The last fetch failure, so a table can render inline instead of only toasting. */
  error: Ref<unknown>;
  collection: Ref<Collection<TItem>>;
  filter: WritableComputedRef<TFilter>;
  sort: WritableComputedRef<DataTableSortData<TItem>>;
  pagination: WritableComputedRef<TablePaginationData>;
  setPage: (page: number, source?: ChangeSource) => void;
  setFilter: (newFilter: TFilter, source?: ChangeSource) => void;
  refetch: () => Promise<void>;
  markUserIntent: () => void;
}

/**
 * Binds a filter schema to a server-paginated table: filter/sort/pagination state,
 * request payload assembly, fetching, and optional URL sync + persistence.
 */
export function useServerTable<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem extends Array<infer U> ? U : TItem> = PaginationRequestPayload<TItem extends Array<infer U> ? U : TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
>(
  options: UseServerTableOptions<TItem, TPayload, TFilter>,
): UseServerTableReturn<TItem, TPayload, TFilter> {
  const itemsPerPage = useItemsPerPage();

  const {
    fetch: requestData,
    fields,
    filterSchema = {
      // The fallback for a table with no filter schema (a dialog listing rows it never filters).
      // Such a table has no filter bag at all, and neither an empty one nor undefined is provably
      // the TFilter its caller declared, so the hole is stated here rather than at every read.
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
      filters: ref({}) as Ref<TFilter>,
    },
    params = [],
    persist,
    request: { cancelTag, debounce: fetchDebounce = 0 } = {},
    sort: { default: defaultSortBy, fallbackColumn } = {},
    urlState = { mode: 'none' },
  } = options;

  const { markUserIntent, pendingIntent, pendingUrlSource } = useChangeIntent();

  const { filters } = filterSchema;

  // Both derived from the declared fields, and cached against them: a gated field list can change
  // while the table is mounted, and the URL must be read with the keys in play at that moment.
  const behaviourKeys = computed<string[]>(() => behaviourKeysFromFields(toValue(fields) ?? []));
  const routeFilterSchema = computed<Schema | undefined>(() => {
    const declared = toValue(fields);
    return declared ? routeSchemaFromFields(declared) : undefined;
  });

  // Commit callbacks feed the reducer. They are defined before the sub-composables that
  // receive them and call the hoisted `dispatch`.
  const commitSort = (sorting: DataTableSortData<TItem>): void => dispatch({ sorting, type: 'sort-set' });
  const commitPage = (page: number, source: ChangeSource = 'user'): void => dispatch({ page, source, type: 'page-set' });
  const commitLimit = (limit: number): void => dispatch({ limit, type: 'limit-set' });

  const { defaultSorting, internalSorting, sort } = useTableSorting<TItem>(
    defaultSortBy,
    commitSort,
    fallbackColumn,
  );

  const {
    captureTransientValues,
    filterPersistedQuery,
    resetTransientValues,
    restorePersistedFilter,
    savePersistedFilter,
  } = useTablePersistence(urlState, persist);

  const { collection, error, isLoading, refetch } = useTableData<TItem, TPayload>(
    requestData,
    // Annotated because `requestPayload` is declared below: without it TypeScript walks
    // the cycle (data -> pagination -> requestPayload -> data) and gives up with `any`.
    // eslint-disable-next-line @typescript-eslint/no-use-before-define -- lazy thunk; only invoked after requestPayload is defined below
    (): ComputedRef<TPayload> => requestPayload,
    cancelTag,
  );

  const { internalPagination, pagination, setPage } = useTablePagination<TItem>(
    itemsPerPage,
    collection,
    commitPage,
    commitLimit,
  );

  const requestPayload = computed<TPayload>(() => {
    const { limit, page } = get(internalPagination);
    const offset = (page - 1) * limit;

    const merged = mergeParams(params, 'request', get(filters) ?? {});
    const transformed = transformFilters(merged, get(behaviourKeys));

    // The one assertion left here, and the boundary it belongs to: what a table sends is its
    // filter bag plus whatever its param sources contribute, which only the caller's own payload
    // type describes. Assembling it from typed parts is what would retire this.
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return {
      ...transformed,
      limit,
      offset,
      ...getApiSortingParams(get(internalSorting), defaultSorting()),
    } as TPayload;
  });

  const filter = computed<TFilter>({
    get() {
      return get(filters);
    },
    set(value: TFilter) {
      dispatch({ filter: value, source: 'user', type: 'filter-set' });
    },
  });

  const { getQuery, writeUrlState } = useUrlStateSync<TItem, TFilter>({
    captureTransientValues,
    defaultSorting,
    fallbackColumn,
    filters,
    internalPagination,
    internalSorting,
    itemsPerPage,
    pendingIntent,
    pendingUrlSource,
    resetTransientValues,
    restorePersistedFilter,
    params,
    routeFilterSchema: (): Schema | undefined => get(routeFilterSchema),
    urlState,
  });

  /**
   * Updates the filter. Defaults to `programmatic`, which does not write back to
   * the URL: the old `updateFilter` in all but name.
   */
  const setFilter = (newFilter: TFilter, source: ChangeSource = 'programmatic'): void => {
    dispatch({ filter: newFilter, source, type: 'filter-set' });
  };

  /**
   * Applies a table event through the pure reducer and writes the changed state slices
   * back to their refs. The reducer's `effects` (fetch/persist/push-url) are not consumed
   * here yet; those stay driven by the `requestPayload` and url-only watchers below.
   * Wiring the effect side is the follow-up that turns persistence and URL sync into
   * channels (Stage 5). The reducer already owns the transitions, which is what fixes the
   * request-param page reset (8b) and collapses a filter change plus its page reset into
   * one atomic state update (one fetch, no cascade).
   */
  function dispatch(event: TableEvent<TFilter, TItem>): void {
    const before: TableState<TFilter, TItem> = {
      filter: get(filters),
      limit: get(internalPagination).limit,
      page: get(internalPagination).page,
      pendingIntent: get(pendingIntent),
      sorting: get(internalSorting),
    };
    const { state } = reduce(before, event);

    if (!isEqual(before.filter, state.filter))
      set(filters, state.filter);
    if (!isEqual(before.sorting, state.sorting))
      set(internalSorting, state.sorting);
    if (before.page !== state.page || before.limit !== state.limit)
      set(internalPagination, { ...get(internalPagination), limit: state.limit, page: state.page });
    if (before.pendingIntent !== state.pendingIntent)
      set(pendingIntent, state.pendingIntent);
  }

  /** Sources that reach both the request and the URL. Changing one resets to page 1. */
  const sharedSourceValues = computed<Record<string, unknown>>(
    () => collectSources(params, 'url', source => source.to === 'both'),
  );

  /**
   * Request-only sources reach the payload but not the URL. Changing one resets to page 1
   * (8b parity) without attributing user intent, so no URL write is earned and route
   * filter state is never clobbered.
   */
  const requestSourceValues = computed<Record<string, unknown>>(
    () => collectSources(params, 'request', source => source.to === 'request'),
  );

  /**
   * URL-only sources never reach `requestPayload`, so no fetch fires for them and the
   * URL would go stale. They get their own write.
   */
  const urlOnlySourceValues = computed<Record<string, unknown>>(
    () => collectSources(params, 'url', source => source.to === 'url'),
  );

  watch(sharedSourceValues, (values, oldValues) => {
    if (!isEqual(values, oldValues))
      dispatch({ to: 'both', type: 'param-changed' });
  });

  watch(requestSourceValues, (values, oldValues) => {
    if (!isEqual(values, oldValues))
      dispatch({ to: 'request', type: 'param-changed' });
  });

  watch(urlOnlySourceValues, async (params, oldParams) => {
    if (isEqual(params, oldParams))
      return;

    markUserIntent();
    await writeUrlState();
  });

  const fetchHandler = async (params: TPayload, op: TPayload): Promise<void> => {
    if (isEqual(params, op))
      return;

    savePersistedFilter(filterPersistedQuery(getQuery()));

    await writeUrlState();
    await refetch();
  };

  if (fetchDebounce > 0) {
    watchDebounced(requestPayload, fetchHandler, { debounce: fetchDebounce });
  }
  else {
    watch(requestPayload, fetchHandler);
  }

  return {
    collection,
    error,
    filter,
    isLoading,
    markUserIntent,
    pagination,
    refetch,
    requestPayload,
    setFilter,
    setPage,
    sort,
  };
}
