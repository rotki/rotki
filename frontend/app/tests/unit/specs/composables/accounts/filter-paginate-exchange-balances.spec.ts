import { type MaybeRef } from '@vueuse/shared';
import flushPromises from 'flush-promises';
import { type Ref } from 'vue';
import { Zero } from '@/utils/bignumbers';
import {
  type ExchangeSavingsCollection,
  type ExchangeSavingsEvent,
  type ExchangeSavingsRequestPayload,
  SupportedExchange
} from '@/types/exchanges';
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
  let fetchExchangeSavings: (
    payload: MaybeRef<ExchangeSavingsRequestPayload>
  ) => Promise<ExchangeSavingsCollection>;
  const exchange: MaybeRef<SupportedExchange> = ref(SupportedExchange.BINANCE);
  const mainPage: Ref<boolean> = ref(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchExchangeSavings = useExchangeBalancesStore().fetchExchangeSavings;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::exchanges/BinanceSavingDetail.vue', () => {
    const extraParams = computed(() => ({
      location: get(exchange).toString()
    }));

    const defaultCollectionState = (): ExchangeSavingsCollection => ({
      found: 0,
      limit: 0,
      data: [],
      total: 0,
      totalUsdValue: Zero,
      assets: [],
      received: []
    });

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
      } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload,
        ExchangeSavingsEvent,
        ExchangeSavingsCollection
      >(exchange, mainPage, useEmptyFilter, fetchExchangeSavings, {
        defaultCollection: defaultCollectionState,
        extraParams,
        defaultSortBy: {
          ascending: [true]
        }
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual(undefined);
      expect(get(options).sortBy[0]).toEqual('timestamp');
      expect(get(options).sortDesc[0]).toEqual(true);
      expect(get(options).sortBy).toHaveLength(1);
      expect(get(options).sortDesc).toHaveLength(1);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).assets).toHaveLength(0);
      expect(get(state).received).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toEqual(260);
    });

    test('check the return types', async () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload,
        ExchangeSavingsEvent,
        ExchangeSavingsCollection
      >(exchange, mainPage, useEmptyFilter, fetchExchangeSavings, {
        defaultCollection: defaultCollectionState,
        extraParams,
        defaultSortBy: {
          ascending: [true]
        }
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<ExchangeSavingsCollection>();
      expectTypeOf(get(state).data).toEqualTypeOf<ExchangeSavingsEvent[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
      expectTypeOf(get(matchers)).toEqualTypeOf<undefined[]>();
    });

    test('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortDesc: ['false'] };

      const { isLoading, state } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload,
        ExchangeSavingsEvent,
        ExchangeSavingsCollection
      >(exchange, mainPage, useEmptyFilter, fetchExchangeSavings, {
        defaultCollection: defaultCollectionState,
        extraParams,
        defaultSortBy: {
          ascending: [true]
        }
      });

      await router.push({
        query
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<ExchangeSavingsCollection>(get(state));
      assertType<ExchangeSavingsEvent[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).assets).toHaveLength(2);
      expect(get(state).received).toHaveLength(2);
      expect(get(state).found).toEqual(260);
      expect(get(state).total).toEqual(260);
    });
  });
});
