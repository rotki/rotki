/* eslint-disable max-lines */
import { Severity } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { FilterBehaviour, type MatchedKeywordWithBehaviour, type SearchMatcher } from '@/types/filtering';
import { defaultCollectionState } from '@/utils/collection';
import { logger } from '@/utils/logging';
import { nonEmptyProperties } from '@/utils/data';
import { useNotificationsStore } from '@/store/notifications';
import { applyPaginationDefaults, applySortingDefaults, getApiSortingParams, parseQueryHistory, parseQueryPagination } from '@/composables/use-pagination-filter/utils';
import { useItemsPerPage } from '@/composables/session/use-items-per-page';
import type { LocationQuery, RawLocationQuery } from '@/types/route';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRef } from '@vueuse/core';
import type { AxiosError } from 'axios';
import type { PaginationRequestPayload } from '@/types/common';
import type { Collection } from '@/types/collection';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { FilterSchema, Sorting } from '@/composables/use-pagination-filter/types';

type Params<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem>,
> = Partial<Omit<TPayload, keyof PaginationRequestPayload<TItem>>>;

interface UsePaginationFiltersOptions<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem> = PaginationRequestPayload<TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
  TSuggestionMatcher extends SearchMatcher<string, string> | void = undefined,
> {
  history?: false | 'router' | 'external';
  locationOverview?: Ref<string>;
  filterSchema?: () => FilterSchema<TFilter, TSuggestionMatcher>;
  onUpdateFilters?: (query: LocationQuery) => void;
  extraParams?: ComputedRef<RawLocationQuery>;
  requestParams?: ComputedRef<Params<TItem, TPayload>>;
  defaultParams?: ComputedRef<Params<TItem, TPayload>>;
  defaultSortBy?: DataTableSortData<TItem>;
  query?: Ref<LocationQuery>;
  queryParamsOnly?: ComputedRef<RawLocationQuery>;
}

interface UsePaginationFilterReturn<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem> = PaginationRequestPayload<TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
  TSuggestionMatcher extends SearchMatcher<string, string> | void = undefined,
> {
  pageParams: ComputedRef<TPayload>;
  isLoading: Ref<boolean>;
  userAction: Ref<boolean>;
  state: Ref<Collection<TItem>>;
  filters: WritableComputedRef<TFilter>;
  matchers: ComputedRef<TSuggestionMatcher[]>;
  sort: WritableComputedRef<DataTableSortData<TItem>>;
  pagination: WritableComputedRef<TablePaginationData>;
  setPage: (page: number, action?: boolean) => void;
  fetchData: () => Promise<void>;
  updateFilter: (newFilter: TFilter) => void;
}

/**
 * Creates a universal pagination and filter structure
 * given the required fields, can manage pagination and filtering and data
 * fetching when params change
 * @template T,U,V,S,W,X
 * @param {(payload: MaybeRef<U>) => Promise<Collection<V>>} requestData
 * @param {{onUpdateFilters?: (query: LocationQuery) => void, extraParams?: ComputedRef<LocationQuery>, queryParamsOnly?: ComputedRef<LocationQuery>, customPageParams?: ComputedRef<Partial<U>>, defaultSortBy?: {pagination?: keyof T, pageParams?: (keyof T)[], pageParamsAsc?: boolean[]}}} options
 */
export function usePaginationFilters<
  TItem extends NonNullable<unknown>,
  TPayload extends PaginationRequestPayload<TItem> = PaginationRequestPayload<TItem>,
  TFilter extends MatchedKeywordWithBehaviour<string> | void = undefined,
  TSuggestionMatcher extends SearchMatcher<string, string> | void = undefined,
>(
  requestData: (payload: MaybeRef<TPayload>) => Promise<Collection<TItem>>,
  options: UsePaginationFiltersOptions<TItem, TPayload, TFilter, TSuggestionMatcher> = {},
): UsePaginationFilterReturn<TItem, TPayload, TFilter, TSuggestionMatcher> {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const itemsPerPage = useItemsPerPage();
  const router = useRouter();
  const route = useRoute();
  const userAction = ref<boolean>(false);
  const internalSorting = ref<Sorting<TItem>>(markRaw(applySortingDefaults(options.defaultSortBy))) as Ref<Sorting<TItem>>;
  const internalPagination = ref<TablePaginationData>(applyPaginationDefaults(get(itemsPerPage)));

  const {
    defaultParams,
    defaultSortBy,
    // giving it a default value since it is watched, for cases where there are no extra params
    extraParams = computed<LocationQuery>(() => ({})),
    filterSchema = (): FilterSchema<TFilter, TSuggestionMatcher> => ({
      filters: ref({}) as Ref<TFilter>,
      matchers: computed<TSuggestionMatcher[]>(() => []),
      RouteFilterSchema: undefined,
    }),
    history = false,
    locationOverview,
    onUpdateFilters,
    query = ref<LocationQuery>({}),
    queryParamsOnly = computed<LocationQuery>(() => ({})),
    requestParams,
  } = options;

  const defaultSorting = (): Sorting<TItem> => applySortingDefaults(defaultSortBy);

  const { filters, matchers, RouteFilterSchema } = filterSchema();

  const sort = computed<DataTableSortData<TItem>>({
    get() {
      return get(internalSorting) as DataTableSortData<TItem>;
    },
    set(sort) {
      set(userAction, true);
      set(internalSorting, sort);
    },
  });

  const transformFilters = (filters: TFilter): TFilter => {
    const matchersVal = get(matchers);

    if (typeof filters !== 'object' || matchersVal.length === 0)
      return filters;

    const newFilters = { ...filters };

    matchersVal.forEach((matcher) => {
      if (typeof matcher !== 'object' || !('string' in matcher) || !matcher.behaviourRequired)
        return;

      const keyValue = matcher.keyValue;
      const key = matcher.key;

      const usedKey = keyValue ?? key;

      if (usedKey in filters) {
        const data = filters[usedKey];
        if (!data)
          return;

        if (typeof data === 'object' && !Array.isArray(data)) {
          if (data.values && usedKey in newFilters) {
            newFilters[usedKey] = {
              behaviour: data.behaviour ?? FilterBehaviour.INCLUDE,
              values: data.values,
            };
          }
          return;
        }

        let formattedData: string | string[] | boolean = data;
        let exclude = false;

        if (matcher.allowExclusion) {
          if (typeof data === 'string' && data.startsWith('!')) {
            exclude = true;
            formattedData = data.substring(1);
          }
          else if (Array.isArray(data) && data.length > 0 && data[0].startsWith('!')) {
            exclude = true;
            formattedData = data.map(item => (item.startsWith('!') ? item.substring(1) : item));
          }
        }

        newFilters[usedKey] = {
          behaviour: exclude ? FilterBehaviour.EXCLUDE : FilterBehaviour.INCLUDE,
          values: formattedData,
        };
      }
    });

    return newFilters;
  };

  const pageParams = computed<TPayload>(() => {
    const { limit, page } = get(internalPagination);
    const offset = (page - 1) * limit;

    const selectedFilters = get(filters);
    const location = get(locationOverview);
    if (location && typeof selectedFilters === 'object' && 'location' in selectedFilters)
      selectedFilters.location = location;

    const transformedFilters = {
      ...(get(defaultParams) ?? {}),
      ...selectedFilters,
      ...get(extraParams),
      ...get(queryParamsOnly),
      ...nonEmptyProperties(get(requestParams) ?? {}),
    };

    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return {
      ...transformFilters(transformedFilters) as Params<TItem, any>,
      limit,
      offset,
      ...getApiSortingParams(get(internalSorting), defaultSorting()),
    } as TPayload; // todo: figure out a way to not typecast
  });

  const { execute, isLoading, state } = useAsyncState<Collection<TItem>, MaybeRef<TPayload>[]>(
    requestData,
    defaultCollectionState<TItem>(),
    {
      delay: 0,
      immediate: false,
      onError(e) {
        const error = e as AxiosError<{ message: string }>;
        const path = error.config?.url;
        let { code, message } = error;

        if (error.response) {
          message = error.response.data.message;
          code = error.response.status.toString();
        }

        logger.error(error);
        if (Number(code) >= 400) {
          notify({
            display: true,
            message: t('error.generic.message', { code, message, path }),
            severity: Severity.ERROR,
            title: t('error.generic.title'),
          });
        }
      },
      resetOnExecute: false,
    },
  );

  const pagination = computed<TablePaginationData>({
    get() {
      const { limit, page } = get(internalPagination);
      const { found: total, limit: entriesLimit } = get(state);
      return {
        limit,
        page,
        total: entriesLimit > 0 && entriesLimit < total ? entriesLimit : total,
      };
    },
    set(pagination) {
      set(userAction, true);
      const currentPagination = get(internalPagination);
      set(internalPagination, {
        ...currentPagination,
        limit: pagination?.limit ?? currentPagination.limit,
        page: pagination?.page ?? currentPagination.page,
      });
    },
  });

  const filter = computed<TFilter>({
    get() {
      return get(filters);
    },
    set(value: TFilter) {
      set(userAction, true);
      set(filters, value);
    },
  });

  /**
   * Triggered on route change and on component mount
   * sets the pagination and filters values from route query
   */
  const applyRouteFilter = (): void => {
    const hasHistory = get(history);
    if (hasHistory === false)
      return;

    const routeQuery = hasHistory === 'router' ? get(route).query : get(query);

    if (isEmpty(routeQuery)) {
      // for empty query, we reset the filters, and pagination to defaults
      onUpdateFilters?.(routeQuery);
      set(filters, RouteFilterSchema?.parse({}));
      set(internalPagination, applyPaginationDefaults(get(itemsPerPage)));
      set(internalSorting, defaultSorting());
      return;
    }

    onUpdateFilters?.(routeQuery);
    set(filters, RouteFilterSchema?.parse(routeQuery));
    set(internalPagination, parseQueryPagination(routeQuery, get(internalPagination)));
    set(internalSorting, parseQueryHistory(routeQuery, defaultSorting()));
  };

  /**
   * Returns the parsed pagination and filter query params
   * @returns {LocationQuery}
   */
  const getQuery = (): LocationQuery => {
    const { limit, page } = get(internalPagination);
    const sorting = get(internalSorting);
    const selectedFilters = get(filters);

    const location = get(locationOverview);
    if (location && typeof selectedFilters === 'object' && 'location' in selectedFilters)
      selectedFilters.location = location;

    const extraParamsConverted = Object.fromEntries(
      Object.entries(get(extraParams)).map(([key, value]) => [key, value?.toString()]),
    );

    const queryParamsOnlyConverted = Object.fromEntries(
      Object.entries(get(queryParamsOnly)).map(([key, value]) => [key, value?.toString()]),
    );

    const sortParams = isEqual(sorting, defaultSorting())
      ? undefined
      : {
          sort: Array.isArray(sorting) ? sorting.map(item => item.column) : [sorting.column],
          sortOrder: Array.isArray(sorting) ? sorting.map(item => item.direction) : [sorting.direction],
        };

    return {
      limit: limit.toString(),
      ...(page > 1 ? { page: page.toString() } : {}),
      ...sortParams,
      ...selectedFilters,
      ...nonEmptyProperties(extraParamsConverted, true),
      ...nonEmptyProperties(queryParamsOnlyConverted, true),
    };
  };

  /**
   * Hits the api to fetch data based on pagination/filter changes
   * @returns {Promise<void>}
   */
  const fetchData = async (): Promise<void> => {
    await execute(0, pageParams);
  };

  /**
   * Updates pagination data for just the current page
   * @param {number} page
   * @param {boolean} action
   */
  const setPage = (page: number, action: boolean = true): void => {
    if (action)
      set(userAction, true);
    set(internalPagination, { ...get(internalPagination), page });
  };

  /**
   * Updates the filters without triggering a user action
   * @template W
   * @param {W} newFilter
   */
  const updateFilter = (newFilter: TFilter): void => {
    set(filters, newFilter);
  };

  onBeforeMount(() => {
    applyRouteFilter();
  });

  watch(route, () => {
    set(userAction, false);
    applyRouteFilter();
  });

  watch([filters, extraParams], ([filters, extraParams], [oldFilters, oldExtraParams]) => {
    const filterEquals = isEqual(filters, oldFilters);
    const paramEquals = isEqual(extraParams, oldExtraParams);

    if (filterEquals && paramEquals)
      return;

    setPage(1, !paramEquals);
  });

  watch(queryParamsOnly, (params, op) => {
    if (isEqual(params, op))
      return;

    set(userAction, true);
  });

  watch(pageParams, async (params, op) => {
    if (isEqual(params, op))
      return;

    const hasHistory = get(history);
    if (get(userAction) && hasHistory !== false) {
      // Route should only be updated on user action otherwise it messes with forward navigation.
      const routeQuery = getQuery();
      // prevent pushing same route
      if (!isEqual(route.query, routeQuery)) {
        if (hasHistory === 'router') {
          await router.push({ query: routeQuery });
        }
        else {
          set(query, routeQuery);
        }
        set(userAction, false);
      }
    }

    await fetchData();
  });

  return {
    fetchData,
    filters: filter,
    isLoading,
    matchers,
    pageParams,
    pagination,
    setPage,
    sort,
    state,
    updateFilter,
    userAction,
  };
}
