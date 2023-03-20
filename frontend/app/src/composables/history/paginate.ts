import { type ComputedRef, type Ref, type UnwrapRef } from 'vue';
import dropRight from 'lodash/dropRight';
import { type ZodSchema } from 'zod';
import isEqual from 'lodash/isEqual';
import { type MaybeRef } from '@vueuse/core';
import { type TablePagination } from '@/types/pagination';
import { defaultCollectionState, defaultOptions } from '@/utils/collection';
import { RouterPaginationOptionsSchema } from '@/types/route';
import { type Collection } from '@/types/collection';

interface FilterSchema {
  filters: Ref;
  matchers: ComputedRef;

  updateFilter(v: any): void;

  RouteFilterSchema: ZodSchema;
}

export const useHistoryPagination = <T extends Object, R, S>(
  locationOverview: Ref,
  mainPage: Ref<boolean>,
  filterSchema: () => FilterSchema,
  fetchAssetData: (payload: MaybeRef<R>) => Promise<Collection<S>>,
  extraParams?: {}
) => {
  const route = useRoute();
  const options: Ref<TablePagination<T>> = ref(defaultOptions<T>());
  const userAction: Ref<boolean> = ref(false);
  const { filters, matchers, updateFilter, RouteFilterSchema } = filterSchema();

  const pageParams: ComputedRef<R> = computed(() => {
    const { itemsPerPage, page, sortBy, sortDesc } = get(options);
    const offset = (page - 1) * itemsPerPage;

    const selectedFilters = get(filters);
    const overview = get(locationOverview);
    if (overview) {
      selectedFilters.location = overview;
    }

    return {
      ...selectedFilters,
      ...extraParams,
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy?.length > 0 ? sortBy : ['timestamp'],
      ascending:
        sortDesc && sortDesc.length > 1
          ? dropRight(sortDesc).map(bool => !bool)
          : [false]
    };
  });

  const { isLoading, state, execute } = useAsyncState<
    Collection<S>,
    MaybeRef<R>[]
  >(args => fetchAssetData(args), defaultCollectionState(), {
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

    updateFilter(parsedFilters);
    set(options, {
      ...get(options),
      ...parsedOptions
    });
  };

  // const fetchData = async (): Promise<void> => {
  //     await execute(0, pageParams);
  // };

  watch(route, () => {
    set(userAction, false);
    applyRouteFilter();
  });

  onBeforeMount(() => {
    applyRouteFilter();
  });

  watch(filters, async (filters, oldFilters) => {
    if (isEqual(filters, oldFilters)) {
      return;
    }

    set(options, { ...get(options), page: 1 });
  });

  const setPage = (page: number) => {
    set(userAction, true);
    set(options, { ...get(options), page });
  };

  const setOptions = (newOptions: TablePagination<T>) => {
    set(userAction, true);
    set(options, newOptions);
  };

  const setFilter = (newFilter: UnwrapRef<typeof filters>) => {
    set(userAction, true);
    updateFilter(newFilter);
  };

  return {
    pageParams,
    applyRouteFilter,
    matchers,
    setPage,
    setOptions,
    setFilter,
    isLoading,
    state,
    execute
  };
};
