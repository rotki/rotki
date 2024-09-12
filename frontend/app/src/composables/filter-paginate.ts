/* eslint-disable max-lines */
import { Severity } from '@rotki/common';
import { isEmpty, isEqual } from 'lodash-es';
import { type LocationQuery, type RawLocationQuery, RouterPaginationOptionsSchema } from '@/types/route';
import { FilterBehaviour, type MatchedKeywordWithBehaviour, type SearchMatcher } from '@/types/filtering';
import type { DataTableSortColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { MaybeRef } from '@vueuse/core';
import type { AxiosError } from 'axios';
import type { ZodSchema } from 'zod';
import type { PaginationRequestPayload } from '@/types/common';
import type { Collection } from '@/types/collection';
import type { TablePagination } from '@/types/pagination';

export interface FilterSchema<F, M> {
  filters: Ref<F>;
  matchers: ComputedRef<M[]>;
  RouteFilterSchema?: ZodSchema;
}

export type TableRowKey<T> = keyof T extends string ? keyof T : never;

interface UsePaginationFiltersOptions<
  T extends NonNullable<unknown>,
  U = PaginationRequestPayload<T>,
  V extends NonNullable<unknown> = T,
  S extends Collection<V> = Collection<V>,
> {
  onUpdateFilters?: (query: LocationQuery) => void;
  extraParams?: ComputedRef<RawLocationQuery>;
  customPageParams?: ComputedRef<Partial<U>>;
  defaultParams?: ComputedRef<Partial<U> | undefined>;
  defaultCollection?: () => S;
  defaultSortBy?: {
    // If it's an array, then multiple sorts are applied; otherwise, it is a single sort.
    key?: keyof V | (keyof V)[];
    ascending?: boolean[];
  };
}

interface UsePaginationFilterReturn<
  T extends NonNullable<unknown>,
  U = PaginationRequestPayload<T>,
  V extends NonNullable<unknown> = T,
  S extends Collection<V> = Collection<V>,
  W extends MatchedKeywordWithBehaviour<string> | void = undefined,
  X extends SearchMatcher<string, string> | void = undefined,
> {
  pageParams: ComputedRef<U>;
  selected: Ref<V[]>;
  openDialog: Ref<boolean>;
  editableItem: Ref<V | undefined>;
  itemsToDelete: Ref<V[]>;
  confirmationMessage: Ref<string>;
  expanded: Ref<V[]>;
  isLoading: Ref<boolean>;
  userAction: Ref<boolean>;
  state: Ref<S>;
  filters: WritableComputedRef<W>;
  matchers: ComputedRef<X[]>;
  sort: WritableComputedRef<DataTableSortData<V>>;
  pagination: WritableComputedRef<TablePaginationData>;
  setPage: (page: number, action?: boolean) => void;
  applyRouteFilter: () => void;
  fetchData: () => Promise<void>;
  updateFilter: (newFilter: W) => void;
}

/**
 * Creates a universal pagination and filter structure
 * given the required fields, can manage pagination and filtering and data
 * fetching when params change
 * @template T,U,V,S,W,X
 * @param {MaybeRef<string | null>} locationOverview
 * @param {MaybeRef<boolean>} mainPage
 * @param {() => FilterSchema<W, X, Y>} filterSchema
 * @param {(payload: MaybeRef<U>) => Promise<Collection<V>>} fetchAssetData
 * @param {{onUpdateFilters?: (query: LocationQuery) => void, extraParams?: ComputedRef<LocationQuery>, customPageParams?: ComputedRef<Partial<U>>, defaultSortBy?: {pagination?: keyof T, pageParams?: (keyof T)[], pageParamsAsc?: boolean[]}}} options
 */
export function usePaginationFilters<
  T extends NonNullable<unknown>,
  U = PaginationRequestPayload<T>,
  V extends NonNullable<unknown> = T,
  S extends Collection<V> = Collection<V>,
  W extends MatchedKeywordWithBehaviour<string> | void = undefined,
  X extends SearchMatcher<string, string> | void = undefined,
>(
  locationOverview: MaybeRef<string | null>,
  mainPage: MaybeRef<boolean>,
  filterSchema: () => FilterSchema<W, X>,
  fetchAssetData: (payload: MaybeRef<U>) => Promise<S>,
  options: UsePaginationFiltersOptions<T, U, V, S> = {},
): UsePaginationFilterReturn<T, U, V, S, W, X> {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const router = useRouter();
  const route = useRoute();
  const paginationOptions = ref(markRaw(defaultOptions<V>(options.defaultSortBy)));
  const selected = ref<V[]>([]) as Ref<V[]>;
  const openDialog = ref<boolean>(false);
  const editableItem = ref<V>();
  const itemsToDelete = ref<V[]>([]) as Ref<V[]>;
  const confirmationMessage = ref<string>('');
  const expanded = ref<V[]>([]) as Ref<V[]>;
  const userAction = ref<boolean>(false);

  const {
    onUpdateFilters,
    defaultCollection,
    // giving it a default value since it is watched, for cases where there are no extra params
    extraParams = computed<LocationQuery>(() => ({})),
    customPageParams,
    defaultParams,
    defaultSortBy,
  } = options;

  const { filters, matchers, RouteFilterSchema } = filterSchema();

  const sort = computed<DataTableSortData<V>>({
    get() {
      const opts = get(paginationOptions);
      if (opts.singleSort) {
        if (opts.sortBy.length === 0)
          return [];

        return {
          column: opts.sortBy[0] as TableRowKey<V>,
          direction: opts.sortDesc?.[0] ? 'desc' : 'asc',
        } satisfies DataTableSortColumn<V>;
      }

      return opts.sortBy.map(
        (sort, index) =>
          ({
            column: sort as TableRowKey<V>,
            direction: opts.sortDesc?.[index] ? 'desc' : 'asc',
          }) satisfies DataTableSortColumn<V>,
      );
    },
    set(sort) {
      set(userAction, true);
      if (Array.isArray(sort)) {
        set(paginationOptions, {
          ...get(paginationOptions),
          sortBy: sort.map(col => col.column as keyof V).filter(key => !!key),
          sortDesc: sort.map(col => col.direction === 'desc'),
        });
      }
      else {
        set(paginationOptions, {
          ...get(paginationOptions),
          sortBy: sort?.column ? [sort.column as keyof V] : [],
          sortDesc: sort?.column ? [sort.direction === 'desc'] : [],
        });
      }
    },
  });

  const transformFilters = (filters: W): W => {
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

  const pageParams = computed<U>(() => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(paginationOptions);
    const offset = (page - 1) * itemsPerPage;

    const selectedFilters = get(filters);
    const location = get(locationOverview);
    if (location && typeof selectedFilters === 'object' && 'location' in selectedFilters)
      selectedFilters.location = location;

    const transformedFilters = {
      ...(get(defaultParams) ?? {}),
      ...selectedFilters,
      ...get(extraParams),
      ...nonEmptyProperties(get(customPageParams) ?? {}),
    };

    const orderByAttributes = sortBy?.length > 0 ? sortBy : arrayify(defaultSortBy?.key ?? 'timestamp');

    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return {
      ...transformFilters(transformedFilters),
      limit: itemsPerPage,
      offset,
      orderByAttributes: orderByAttributes.map(item => (typeof item === 'string' ? transformCase(item) : item)),
      ascending: sortBy?.length > 0 ? sortDesc.map(bool => !bool) : defaultSortBy?.ascending ?? [false],
    } as U; // todo: figure out a way to not typecast
  });

  const getCollectionDefault = (): S => {
    if (defaultCollection)
      return defaultCollection();

    return defaultCollectionState<V>() as S;
  };

  const { isLoading, state, execute } = useAsyncState<S, MaybeRef<U>[]>(fetchAssetData, getCollectionDefault(), {
    immediate: false,
    resetOnExecute: false,
    delay: 0,
    onError(e) {
      const error = e as AxiosError<{ message: string }>;
      const path = error.config?.url;
      let { message, code } = error;

      if (error.response) {
        message = error.response.data.message;
        code = error.response.status.toString();
      }

      logger.error(error);
      if (Number(code) >= 400) {
        notify({
          title: t('error.generic.title'),
          message: t('error.generic.message', { code, message, path }),
          severity: Severity.ERROR,
          display: true,
        });
      }
    },
  });

  const pagination = computed<TablePaginationData>({
    get() {
      const opts = get(paginationOptions);
      return {
        total: get(state).found,
        page: opts.page,
        limit: opts.itemsPerPage,
      };
    },
    set(pagination) {
      set(userAction, true);
      const opts = get(paginationOptions);
      set(paginationOptions, {
        ...opts,
        page: pagination?.page ?? opts.page,
        itemsPerPage: pagination?.limit ?? opts.itemsPerPage,
      });
    },
  });

  const filter = computed<W>({
    get() {
      return get(filters);
    },
    set(value: W) {
      set(userAction, true);
      set(filters, value);
    },
  });

  /**
   * Updates pagination options
   * @template T
   * @param {TablePagination<T>} newOptions
   */
  const setOptions = (newOptions: TablePagination<V>): void => {
    set(userAction, true);
    set(paginationOptions, newOptions);
  };

  /**
   * Triggered on route change and on component mount
   * sets the pagination and filters values from route query
   */
  const applyRouteFilter = (): void => {
    if (!get(mainPage))
      return;

    const query = get(route).query;

    if (isEmpty(query)) {
      // for empty query, we reset the filters, and pagination to defaults
      onUpdateFilters?.(query);
      set(filters, RouteFilterSchema?.parse({}));
      return setOptions(defaultOptions<V>(options.defaultSortBy));
    }

    const parsedOptions = RouterPaginationOptionsSchema.parse(query);
    const parsedFilters = RouteFilterSchema?.parse(query);

    onUpdateFilters?.(query);

    set(filters, parsedFilters);
    set(paginationOptions, {
      ...get(paginationOptions),
      ...parsedOptions,
    });
  };

  /**
   * Returns the parsed pagination and filter query params
   * @returns {LocationQuery}
   */
  const getQuery = (): LocationQuery => {
    const opts = get(paginationOptions);
    assert(opts);
    const { itemsPerPage, page, sortBy, sortDesc } = opts;

    const selectedFilters = get(filters);

    const location = get(locationOverview);
    if (location && typeof selectedFilters === 'object' && 'location' in selectedFilters)
      selectedFilters.location = location;

    const extraParamsConverted = Object.fromEntries(
      Object.entries(get(extraParams)).map(([key, value]) => [key, value?.toString()]),
    );

    return {
      itemsPerPage: itemsPerPage.toString(),
      page: page.toString(),
      sortBy: sortBy.map(s => s.toString()),
      sortDesc: sortDesc.map(x => x.toString()),
      ...selectedFilters,
      ...extraParamsConverted,
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
  const setPage = (page: number, action = true): void => {
    if (action)
      set(userAction, true);

    set(paginationOptions, { ...get(paginationOptions), page });
  };

  /**
   * Updates the filters without triggering a user action
   * @template W
   * @param {W} newFilter
   */
  const updateFilter = (newFilter: W): void => {
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

  watch(pageParams, async (params, op) => {
    if (isEqual(params, op))
      return;

    if (get(userAction) && get(mainPage)) {
      // Route should only be updated on user action otherwise it messes with forward navigation.
      const query = getQuery();
      // prevent pushing same route
      if (!isEqual(route.query, query)) {
        await router.push({ query });
        set(userAction, false);
      }
    }

    await fetchData();
  });

  return {
    pageParams,
    selected,
    openDialog,
    editableItem,
    itemsToDelete,
    confirmationMessage,
    expanded,
    isLoading,
    userAction,
    state,
    filters: filter,
    matchers,
    sort,
    pagination,
    setPage,
    applyRouteFilter,
    fetchData,
    updateFilter,
  };
}
