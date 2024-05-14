import flushPromises from 'flush-promises';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import type {
  NonFungibleBalance,
  NonFungibleBalancesRequestPayload,
} from '@/types/nfbalances';
import type { LocationQuery } from '@/types/route';
import type Vue from 'vue';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      query: {},
    }),
  ),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(({ query }) => {
      useRoute().query = query;
      return true;
    }),
  }),
}));

vi.mock('vue', async () => {
  const mod = await vi.importActual<Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: Function) => fn()),
  };
});

describe('composables::history/filter-paginate', () => {
  let fetchNonFungibleBalances: (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>
  ) => Promise<Collection<NonFungibleBalance>>;
  const locationOverview: MaybeRef<string | null> = ref('');
  const mainPage: Ref<boolean> = ref(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchNonFungibleBalances = useNonFungibleBalancesStore().fetchNonFungibleBalances;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::accounts/balances/NonFungibleBalances.vue', () => {
    set(locationOverview, '');
    const ignoredAssetsHandling = ref('none');
    const extraParams = computed(() => ({
      includeIgnoredTrades: get(ignoredAssetsHandling),
    }));

    const onUpdateFilters = (query: LocationQuery) => {
      set(ignoredAssetsHandling, query.includeIgnoredTrades);
    };

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const {
        userAction,
        filters,
        sort,
        state,
        fetchData,
        applyRouteFilter,
        isLoading,
      } = usePaginationFilters<NonFungibleBalance>(
        locationOverview,
        mainPage,
        useEmptyFilter,
        fetchNonFungibleBalances,
        {
          onUpdateFilters,
          extraParams,
          defaultSortBy: {
            key: 'name',
            ascending: [true],
          },
        },
      );

      expect(get(userAction)).toBe(true);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual(undefined);
      expect(get(sort)).toHaveLength(1);
      expect(get(sort)).toMatchObject([{
        column: 'name',
        direction: 'asc',
      }]);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(30);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers }
        = usePaginationFilters<NonFungibleBalance>(
          locationOverview,
          mainPage,
          useEmptyFilter,
          fetchNonFungibleBalances,
          {
            onUpdateFilters,
            extraParams,
            defaultSortBy: {
              key: 'name',
              ascending: [true],
            },
          },
        );

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<NonFungibleBalance>>();
      expectTypeOf(get(state).data).toEqualTypeOf<NonFungibleBalance[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
      expectTypeOf(get(matchers)).toEqualTypeOf<undefined[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortDesc: ['false'] };

      const { isLoading, state } = usePaginationFilters<NonFungibleBalance>(
        locationOverview,
        mainPage,
        useEmptyFilter,
        fetchNonFungibleBalances,
        {
          onUpdateFilters,
          extraParams,
          defaultSortBy: {
            key: 'name',
            ascending: [false],
          },
        },
      );

      await router.push({
        query,
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<NonFungibleBalance>>(get(state));
      assertType<NonFungibleBalance[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(9);
      expect(get(state).found).toEqual(29);
      expect(get(state).total).toEqual(30);
    });
  });
});
