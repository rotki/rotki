import { type MaybeRef } from '@vueuse/shared';
import flushPromises from 'flush-promises';
import { type Ref } from 'vue';
import { defaultCollectionState } from '@/utils/collection';
import { type Collection } from '@/types/collection';
import { type LocationQuery } from '@/types/route';
import type { Filters, Matcher } from '@/composables/filters/trades';
import type {
  Trade,
  TradeEntry,
  TradeRequestPayload
} from '@/types/history/trade';
import type Vue from 'vue';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      query: {}
    })
  ),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(({ query }) => {
      useRoute().query = query;
      return true;
    })
  })
}));

vi.mock('vue', async () => {
  const mod = await vi.importActual<Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn()
  };
});

describe('composables::history/filter-paginate', () => {
  let fetchTrades: (
    payload: MaybeRef<TradeRequestPayload>
  ) => Promise<Collection<TradeEntry>>;
  const locationOverview: MaybeRef<string | null> = ref('');
  const mainPage: Ref<boolean> = ref(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchTrades = useTrades().fetchTrades;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/ClosedTrades', () => {
    set(locationOverview, '');
    const hideIgnoredTrades = ref(false);
    const extraParams = computed(() => ({
      includeIgnoredTrades: (!get(hideIgnoredTrades)).toString()
    }));

    const onUpdateFilters = (query: LocationQuery) => {
      set(hideIgnoredTrades, query.includeIgnoredTrades === 'false');
    };

    beforeEach(() => {
      set(mainPage, true);
    });

    test('initialize composable correctly', async () => {
      const {
        userAction,
        filters,
        options,
        state,
        fetchData,
        applyRouteFilter,
        isLoading
      } = useHistoryPaginationFilter<
        Trade,
        TradeRequestPayload,
        TradeEntry,
        Collection<TradeEntry>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        useTradeFilters,
        fetchTrades,
        defaultCollectionState,
        {
          onUpdateFilters,
          extraParams
        }
      );

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(options).sortBy).toHaveLength(1);
      expect(get(options).sortDesc).toHaveLength(1);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(210);
    });

    test('check the return types', async () => {
      const { isLoading, state, filters, matchers } =
        useHistoryPaginationFilter<
          Trade,
          TradeRequestPayload,
          TradeEntry,
          Collection<TradeEntry>,
          Filters,
          Matcher
        >(
          locationOverview,
          mainPage,
          useTradeFilters,
          fetchTrades,
          defaultCollectionState,
          {
            onUpdateFilters,
            extraParams
          }
        );

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<TradeEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<TradeEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    test('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['type'], sortDesc: ['true'] };

      const { isLoading, state } = useHistoryPaginationFilter<
        Trade,
        TradeRequestPayload,
        TradeEntry,
        Collection<TradeEntry>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        useTradeFilters,
        fetchTrades,
        defaultCollectionState,
        {
          onUpdateFilters,
          extraParams
        }
      );

      await router.push({
        query
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<TradeEntry>>(get(state));
      assertType<TradeEntry[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).found).toEqual(210);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(210);
    });
  });
});
