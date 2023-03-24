import { type ComputedRef, type Ref, type UnwrapRef } from 'vue';
import { type ZodSchema } from 'zod';
import isEqual from 'lodash/isEqual';
import { type MaybeRef } from '@vueuse/core';
import { type TablePagination } from '@/types/pagination';
import { defaultCollectionState, defaultOptions } from '@/utils/collection';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';
import { type Collection } from '@/types/collection';
import { assert } from '@/utils/assertions';

interface FilterSchema<F, M> {
  filters: Ref<F>;
  matchers: ComputedRef<M[]>;

  updateFilter(filter: F): void;

  RouteFilterSchema: ZodSchema;
}

export const useHistoryPaginationFilter = <
  T extends Object,
  U,
  V,
  W extends Object,
  X
>(
  locationOverview: MaybeRef<string | null>,
  mainPage: Ref<boolean>,
  filterSchema: () => FilterSchema<W, X>,
  fetchAssetData: (payload: MaybeRef<U>) => Promise<Collection<V>>,
  options: {
    onUpdateFilters?: (query: LocationQuery) => void;
    extraParams?: ComputedRef<LocationQuery>;
    customPageParams?: ComputedRef<Partial<U>>;
  } = {}
) => {
  const router = useRouter();
  const route = useRoute();
  const paginationOptions: Ref<TablePagination<T>> = ref(defaultOptions<T>());
  const selected: Ref<V[]> = ref([]);
  const openDialog: Ref<boolean> = ref(false);
  const editableItem: Ref<V | null> = ref(null);
  const itemsToDelete: Ref<V[]> = ref([]);
  const confirmationMessage: Ref<string> = ref('');
  const expanded: Ref<V[]> = ref([]);
  const userAction: Ref<boolean> = ref(false);

  const { onUpdateFilters, extraParams, customPageParams } = options;

  const { filters, matchers, updateFilter, RouteFilterSchema } = filterSchema();

  const pageParams: ComputedRef<U> = computed(() => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(paginationOptions);
    const offset = (page - 1) * itemsPerPage;

    const selectedFilters = get(filters);
    const overview = get(locationOverview);
    if (overview && 'location' in selectedFilters) {
      selectedFilters.location = overview;
    }

    return {
      ...selectedFilters,
      ...get(extraParams),
      ...get(customPageParams),
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy?.length > 0 ? sortBy : ['timestamp'],
      ascending: sortBy?.length > 0 ? sortDesc.map(bool => !bool) : [false]
    } as U; // todo: figure out a way to not typecast
  });

  const { isLoading, state, execute } = useAsyncState<
    Collection<V>,
    MaybeRef<U>[]
  >(fetchAssetData, defaultCollectionState(), {
    immediate: false,
    resetOnExecute: false,
    delay: 0
  });

  const applyRouteFilter = () => {
    if (!get(mainPage)) {
      return;
    }

    const query = get(route).query;
    const parsedOptions = RouterPaginationOptionsSchema.parse(query);
    const parsedFilters = RouteFilterSchema.parse(query);

    onUpdateFilters?.call(null, query);

    updateFilter(parsedFilters);
    set(paginationOptions, {
      ...get(paginationOptions),
      ...parsedOptions
    });
  };

  const getQuery = (): LocationQuery => {
    const opts = get(paginationOptions);
    assert(opts);
    const { itemsPerPage, page, sortBy, sortDesc } = opts;

    const selectedFilters = get(filters);

    const overview = get(locationOverview);
    if (overview && 'location' in selectedFilters) {
      selectedFilters.location = overview;
    }

    return {
      itemsPerPage: itemsPerPage.toString(),
      page: page.toString(),
      sortBy: sortBy.map(s => s.toString()),
      sortDesc: sortDesc.map(x => x.toString()),
      ...selectedFilters,
      ...get(extraParams)
    };
  };

  const fetchData = async (): Promise<void> => {
    await execute(0, pageParams);
  };

  const setPage = (page: number) => {
    set(userAction, true);
    set(paginationOptions, { ...get(paginationOptions), page });
  };

  const setOptions = (newOptions: TablePagination<T>) => {
    set(userAction, true);
    set(paginationOptions, newOptions);
  };

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
      await router.push({
        query: getQuery()
      });
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
