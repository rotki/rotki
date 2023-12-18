import { Severity } from '@rotki/common/lib/messages';
import { type MaybeRef } from '@vueuse/core';
import { type AxiosError } from 'axios';
import { isEmpty, isEqual } from 'lodash-es';
import { type ZodSchema } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { type Collection } from '@/types/collection';
import { type TablePagination } from '@/types/pagination';
import {
  type LocationQuery,
  type RawLocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';
import {
  FilterBehaviour,
  type MatchedKeywordWithBehaviour,
  type SearchMatcher
} from '@/types/filtering';

interface FilterSchema<F, M> {
  filters: Ref<F>;
  matchers: ComputedRef<M[]>;
  updateFilter: (filter: F) => void;
  RouteFilterSchema: ZodSchema;
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
export const usePaginationFilters = <
  T extends NonNullable<unknown>,
  U = PaginationRequestPayload<T>,
  V extends NonNullable<unknown> = T,
  S extends Collection<V> = Collection<V>,
  W extends MatchedKeywordWithBehaviour<string> | void = undefined,
  X extends SearchMatcher<string, string> | void = undefined
>(
  locationOverview: MaybeRef<string | null>,
  mainPage: MaybeRef<boolean>,
  filterSchema: () => FilterSchema<W, X>,
  fetchAssetData: (payload: MaybeRef<U>) => Promise<S>,
  options: {
    onUpdateFilters?: (query: LocationQuery) => void;
    extraParams?: ComputedRef<LocationQuery>;
    customPageParams?: ComputedRef<Partial<U>>;
    defaultParams?: ComputedRef<Partial<U> | undefined>;
    defaultCollection?: () => S;
    defaultSortBy?: {
      key?: keyof V;
      ascending?: boolean[];
    };
  } = {}
) => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const router = useRouter();
  const route = useRoute();
  const paginationOptions: Ref<TablePagination<V>> = ref(
    defaultOptions<V>(options.defaultSortBy)
  );
  const selected: Ref<V[]> = ref([]);
  const openDialog: Ref<boolean> = ref(false);
  const editableItem: Ref<V | undefined> = ref();
  const itemsToDelete: Ref<V[]> = ref([]);
  const confirmationMessage: Ref<string> = ref('');
  const expanded: Ref<V[]> = ref([]);
  const userAction: Ref<boolean> = ref(false);

  const {
    onUpdateFilters,
    defaultCollection,
    extraParams,
    customPageParams,
    defaultParams,
    defaultSortBy
  } = options;

  const { filters, matchers, updateFilter, RouteFilterSchema } = filterSchema();

  const transformFilters = (filters: W): W => {
    const matchersVal = get(matchers);

    if (typeof filters !== 'object' || matchersVal.length === 0) {
      return filters;
    }

    const newFilters = { ...filters };

    matchersVal.forEach(matcher => {
      if (
        typeof matcher !== 'object' ||
        !('string' in matcher) ||
        !matcher.behaviourRequired
      ) {
        return;
      }

      const keyValue = matcher.keyValue;
      const key = matcher.key;

      const usedKey = keyValue ?? key;

      if (usedKey in filters) {
        const data = filters[usedKey];
        if (!data) {
          return;
        }

        if (typeof data === 'object' && !Array.isArray(data)) {
          if (data.values && usedKey in newFilters) {
            newFilters[usedKey] = {
              behaviour: data.behaviour ?? FilterBehaviour.INCLUDE,
              values: data.values
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
          } else if (
            Array.isArray(data) &&
            data.length > 0 &&
            data[0].startsWith('!')
          ) {
            exclude = true;
            formattedData = data.map(item =>
              item.startsWith('!') ? item.substring(1) : item
            );
          }
        }

        newFilters[usedKey] = {
          behaviour: exclude
            ? FilterBehaviour.EXCLUDE
            : FilterBehaviour.INCLUDE,
          values: formattedData
        };
      }
    });

    return newFilters;
  };

  const pageParams: ComputedRef<U> = computed(() => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(paginationOptions);
    const offset = (page - 1) * itemsPerPage;

    const selectedFilters = get(filters);
    const location = get(locationOverview);
    if (
      location &&
      typeof selectedFilters === 'object' &&
      'location' in selectedFilters
    ) {
      selectedFilters.location = location;
    }

    const transformedFilters = {
      ...(get(defaultParams) ?? {}),
      ...selectedFilters,
      ...get(extraParams),
      ...nonEmptyProperties(get(customPageParams) ?? {})
    };

    const orderByAttributes =
      sortBy?.length > 0 ? sortBy : [defaultSortBy?.key ?? 'timestamp'];

    return {
      ...transformFilters(transformedFilters),
      limit: itemsPerPage,
      offset,
      orderByAttributes: orderByAttributes.map(item =>
        typeof item === 'string' ? transformCase(item) : item
      ),
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
            display: true
          });
        }
      }
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
      return setOptions(defaultOptions<V>(options.defaultSortBy));
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
  const getQuery = (): RawLocationQuery => {
    const opts = get(paginationOptions);
    assert(opts);
    const { itemsPerPage, page, sortBy, sortDesc } = opts;

    const selectedFilters = get(filters);

    const location = get(locationOverview);
    if (
      location &&
      typeof selectedFilters === 'object' &&
      'location' in selectedFilters
    ) {
      selectedFilters.location = location;
    }

    const extraParamsConverted = Object.fromEntries(
      Object.entries(get(extraParams) || {}).map(([key, value]) => [
        key,
        value?.toString()
      ])
    );

    return {
      itemsPerPage: itemsPerPage.toString(),
      page: page.toString(),
      sortBy: sortBy.map(s => s.toString()),
      sortDesc: sortDesc.map(x => x.toString()),
      ...selectedFilters,
      ...extraParamsConverted
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
  const setOptions = (newOptions: TablePagination<V>) => {
    set(userAction, true);
    set(paginationOptions, newOptions);
  };

  /**
   * Updates the filters
   * @template W
   * @param {W} newFilter
   */
  const setFilter = (newFilter: W) => {
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

  watch(
    [filters, extraParams],
    async ([filters, extraParams], [oldFilters, oldExtraParams]) => {
      if (
        isEqual(filters, oldFilters) &&
        isEqual(extraParams, oldExtraParams)
      ) {
        return;
      }

      set(paginationOptions, { ...get(paginationOptions), page: 1 });
    }
  );

  watch(pageParams, async (params, op) => {
    if (isEqual(params, op)) {
      return;
    }
    if (get(userAction) && get(mainPage)) {
      // Route should only be updated on user action otherwise it messes with forward navigation.
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
