import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, Ref, WritableComputedRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { isEqual } from 'es-toolkit';
import { getApiSortingParams } from '@/modules/core/table/pagination-filter-utils';
import { collectSources, mergeParams, type ParamSource, transformFilters } from '@/modules/core/table/param-sources';
import { type ChangeSource, useChangeIntent } from '@/modules/core/table/use-change-intent';
import { useTableData } from '@/modules/core/table/use-table-data';
import { useTablePagination } from '@/modules/core/table/use-table-pagination';
import { type PersistFilterSetting, useTablePersistence } from '@/modules/core/table/use-table-persistence';
import { useTableSorting } from '@/modules/core/table/use-table-sorting';
import { routeWhen, type UrlState, useUrlStateSync } from '@/modules/core/table/use-url-state-sync';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';

// Re-exported so the facade's public surface stays exactly what it was before the
// provenance and URL-sync internals moved into their own modules.
export type { ChangeSource, UrlState };

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
  TSuggestionMatcher extends SearchMatcher<string, string> | void = undefined,
> {
  /** The request function. `TPayload` is inferred from its parameter. */
  fetch: (payload: MaybeRef<TPayload>) => Promise<Collection<TItem>>;
  urlState?: UrlState;
  /**
   * The filter schema itself, not a factory: the caller holds it and reads
   * `matchers` off it. Named `filterSchema` because `filter` is the returned value.
   */
  filterSchema?: FilterSchema<TFilter, TSuggestionMatcher>;
  params?: ParamSource[];
  sort?: TableSortOptions<TItem>;
  /** Absent means no persistence at all. */
  persist?: PersistFilterSetting;
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
  TSuggestionMatcher extends SearchMatcher<string, string> | void = undefined,
>(
  options: UseServerTableOptions<TItem, TPayload, TFilter, TSuggestionMatcher>,
): UseServerTableReturn<TItem, TPayload, TFilter> {
  const itemsPerPage = useItemsPerPage();

  const {
    fetch: requestData,
    filterSchema = {
      filters: ref({}) as Ref<TFilter>,
      matchers: computed<TSuggestionMatcher[]>(() => []),
      RouteFilterSchema: undefined,
    },
    params = [],
    persist,
    request: { cancelTag, debounce: fetchDebounce = 0 } = {},
    sort: { default: defaultSortBy, fallbackColumn } = {},
    urlState = { mode: 'none' },
  } = options;

  const { markSource, markUserIntent, pendingIntent, pendingUrlSource } = useChangeIntent();

  const { defaultSorting, internalSorting, sort } = useTableSorting<TItem>(
    defaultSortBy,
    markUserIntent,
    fallbackColumn,
  );

  const { filters, matchers, RouteFilterSchema } = filterSchema;

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
    (): ComputedRef<TPayload> => requestPayload,
    cancelTag,
  );

  const { internalPagination, pagination, setPage } = useTablePagination<TItem>(
    itemsPerPage,
    collection,
    markSource,
    markUserIntent,
  );

  const requestPayload = computed<TPayload>(() => {
    const { limit, page } = get(internalPagination);
    const offset = (page - 1) * limit;

    const merged = mergeParams(params, 'request', get(filters) ?? {});

    // The merged bag is filter keys plus arbitrary source keys, so it is only
    // nominally TFilter. Both casts are the same debt the old code carried and both
    // die in Stage 4, when the payload is assembled from typed parts instead of
    // spread from one loosely-typed bag.
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    const transformed = transformFilters(merged as TFilter, get(matchers)) as Record<string, unknown>;

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
      markUserIntent();
      set(filters, value);
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
    routeFilterSchema: RouteFilterSchema,
    urlState,
  });

  /**
   * Updates the filter. Defaults to `programmatic`, which does not write back to
   * the URL: the old `updateFilter` in all but name.
   */
  const setFilter = (newFilter: TFilter, source: ChangeSource = 'programmatic'): void => {
    markSource(source);
    set(filters, newFilter);
  };

  /** Sources that reach both the request and the URL. Changing one resets to page 1. */
  const sharedSourceValues = computed<Record<string, unknown>>(
    () => collectSources(params, 'url', source => source.to === 'both'),
  );

  /**
   * URL-only sources never reach `requestPayload`, so no fetch fires for them and the
   * URL would go stale. They get their own write.
   */
  const urlOnlySourceValues = computed<Record<string, unknown>>(
    () => collectSources(params, 'url', source => source.to === 'url'),
  );

  watch([filters, sharedSourceValues], ([filters, params], [oldFilters, oldParams]) => {
    const filterEquals = isEqual(filters, oldFilters);
    const paramEquals = isEqual(params, oldParams);

    if (filterEquals && paramEquals)
      return;

    setPage(1, paramEquals ? 'programmatic' : 'user');
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
