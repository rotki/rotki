import { type MaybeRef } from '@vueuse/core';
import isEmpty from 'lodash/isEmpty';
import isEqual from 'lodash/isEqual';
import keys from 'lodash/keys';
import pick from 'lodash/pick';
import { type ComputedRef, type Ref, type UnwrapRef } from 'vue';
import { type ZodSchema } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { type Collection } from '@/types/collection';
import { type TablePagination } from '@/types/pagination';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';

interface FilterSchema<F, M> {
  filters: Ref<F>;
  matchers: ComputedRef<M[]>;
  updateFilter: (filter: F) => void;
  RouteFilterSchema: ZodSchema;
  transformExclusionFilters?: (filter: F) => F;
}

/**
 * Creates a universal pagination and filter structure
 * given the required fields, can manage pagination and filtering and data
 * fetching when params change
 * @template T,U,V,S,W,X
 * @param {MaybeRef<string | null>} locationOverview
 * @param {MaybeRef<boolean>} mainPage
 * @param {() => FilterSchema<W, X>} filterSchema
 * @param {(payload: MaybeRef<U>) => Promise<Collection<V>>} fetchAssetData
 * @param {{onUpdateFilters?: (query: LocationQuery) => void, extraParams?: ComputedRef<LocationQuery>, customPageParams?: ComputedRef<Partial<U>>, defaultSortBy?: {pagination?: keyof T, pageParams?: (keyof T)[], pageParamsAsc?: boolean[]}}} options
 */
export const usePaginationFilters = <
  T extends Object,
  U = PaginationRequestPayload<T>,
  V = T,
  S extends Collection<V> = Collection<V>,
  W extends Object | void = undefined,
  X = undefined
>(
  locationOverview: MaybeRef<string | null>,
  mainPage: MaybeRef<boolean>,
  filterSchema: () => FilterSchema<W, X>,
  fetchAssetData: (payload: MaybeRef<U>) => Promise<S>,
  options: {
    onUpdateFilters?: (query: LocationQuery) => void;
    extraParams?: ComputedRef<LocationQuery>;
    customPageParams?: ComputedRef<Partial<U>>;
    defaultCollection?: () => S;
    defaultSortBy?: {
      key?: keyof T;
      ascending?: boolean[];
    };
  } = {}
) => {
  const router = useRouter();
  const route = useRoute();
  const paginationOptions: Ref<TablePagination<T>> = ref(
    defaultOptions<T>(options.defaultSortBy)
  );
  const selected: Ref<V[]> = ref([]);
  const openDialog: Ref<boolean> = ref(false);
  const editableItem: Ref<V | null> = ref(null);
  const itemsToDelete: Ref<V[]> = ref([]);
  const confirmationMessage: Ref<string> = ref('');
  const expanded: Ref<V[]> = ref([]);
  const userAction: Ref<boolean> = ref(false);

  const {
    onUpdateFilters,
    defaultCollection,
    extraParams,
    customPageParams,
    defaultSortBy
  } = options;

  const {
    filters,
    matchers,
    updateFilter,
    RouteFilterSchema,
    transformExclusionFilters
  } = filterSchema();

  const pageParams: ComputedRef<U> = computed(() => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(paginationOptions);
    const offset = (page - 1) * itemsPerPage;

    let selectedFilters = get(filters);
    if (transformExclusionFilters) {
      selectedFilters = {
        ...selectedFilters,
        ...transformExclusionFilters(selectedFilters)
      };
    }
    const overview = get(locationOverview);
    if (
      overview &&
      typeof selectedFilters === 'object' &&
      'location' in selectedFilters
    ) {
      selectedFilters.location = overview;
    }

    return {
      ...selectedFilters,
      ...get(extraParams),
      ...nonEmptyProperties(get(customPageParams) ?? {}),
      limit: itemsPerPage,
      offset,
      orderByAttributes:
        sortBy?.length > 0 ? sortBy : [defaultSortBy?.key ?? 'timestamp'],
      ascending:
        sortBy?.length > 0
          ? sortDesc.map(bool => !bool)
          : defaultSortBy?.ascending ?? [false]
    } as U; // todo: figure out a way to not typecast
  });

  const getCollectionDefault = (): S => {
    if (defaultCollection) {
      return defaultCollection();
    }

    return defaultCollectionState<V>() as S;
  };

  const { isLoading, state, execute } = useAsyncState<S, MaybeRef<U>[]>(
    fetchAssetData,
    getCollectionDefault(),
    {
      immediate: false,
      resetOnExecute: false,
      delay: 0
    }
  );

  /**
   * Triggered on route change and on component mount
   * sets the pagination and filters values from route query
   */
  const applyRouteFilter = () => {
    if (!get(mainPage)) {
      return;
    }

    const query = get(route).query;

    if (isEmpty(query)) {
      // for empty query, we reset the filters, and pagination to defaults
      onUpdateFilters?.(query);
      updateFilter(RouteFilterSchema.parse({}));
      return setOptions(defaultOptions<T>(options.defaultSortBy));
    }

    const parsedOptions = RouterPaginationOptionsSchema.parse(query);
    const parsedFilters = RouteFilterSchema.parse(query);

    onUpdateFilters?.(query);

    updateFilter(parsedFilters);
    set(paginationOptions, {
      ...get(paginationOptions),
      ...parsedOptions
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

    const overview = get(locationOverview);
    if (
      overview &&
      typeof selectedFilters === 'object' &&
      'location' in selectedFilters
    ) {
      selectedFilters.location = overview;
    }

    return {
      itemsPerPage: itemsPerPage.toString(),
      page: page.toString(),
      sortBy: sortBy.map(s => s.toString()),
      sortDesc: sortDesc.map(x => x.toString()),
      ...pick(selectedFilters, keys(selectedFilters)),
      ...get(extraParams)
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
   */
  const setPage = (page: number) => {
    set(userAction, true);
    set(paginationOptions, { ...get(paginationOptions), page });
  };

  /**
   * Updates pagination options
   * @template T
   * @param {TablePagination<T>} newOptions
   */
  const setOptions = (newOptions: TablePagination<T>) => {
    set(userAction, true);
    set(paginationOptions, newOptions);
  };

  /**
   * Updates the filters
   * @template W
   * @param {UnwrapRef<Ref<W>>} newFilter
   */
  const setFilter = (newFilter: UnwrapRef<Ref<W>>) => {
    set(userAction, true);
    updateFilter(newFilter);
  };

  onBeforeMount(() => {
    applyRouteFilter();
  });

  watch(route, () => {
    set(userAction, false);
    applyRouteFilter();
  });

  watch(filters, async (filters, oldFilters) => {
    if (isEqual(filters, oldFilters)) {
      return;
    }

    set(paginationOptions, { ...get(paginationOptions), page: 1 });
  });

  watch(pageParams, async (params, op) => {
    if (isEqual(params, op)) {
      return;
    }
    if (get(userAction) && get(mainPage)) {
      // Route should only be updated on user action otherwise it messes with
      // forward navigation.
      const query = getQuery();
      if (isEqual(route.query, query)) {
        // prevent pushing same route
        return;
      }
      await router.push({ query });
      set(userAction, false);
    }

    await fetchData();
  });

  return {
    options: paginationOptions,
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
    filters,
    matchers,
    setPage,
    setOptions,
    setFilter,
    applyRouteFilter,
    updateFilter,
    fetchData
  };
};
