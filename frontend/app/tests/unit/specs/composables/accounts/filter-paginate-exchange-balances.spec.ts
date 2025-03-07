import type { Collection } from '@/types/collection';
import type { ExchangeSavingsCollection, ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/types/exchanges';
import type { AssetBalance } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type * as Vue from 'vue';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';

vi.mock('vue-router', async () => {
  const { ref } = await import('vue');
  const { set } = await import('@vueuse/core');
  const route = ref({
    query: {},
  });
  return {
    useRoute: vi.fn().mockReturnValue(route),
    useRouter: vi.fn().mockReturnValue({
      push: vi.fn(({ query }) => {
        set(route, { query });
        return true;
      }),
    }),
  };
});

vi.mock('vue', async () => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void) => fn()),
  };
});

describe('composables::history/filter-paginate', () => {
  let fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => Promise<ExchangeSavingsCollection>;
  const exchange = ref<string>('binance');
  const mainPage = ref<boolean>(false);
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
    const exchangeReceived = ref<AssetBalance[]>([]);
    const exchangeAssets = ref<string[]>([]);
    const defaultParams = computed(() => ({
      location: get(exchange).toString(),
    }));

    async function fetchSavings(payload: MaybeRef<ExchangeSavingsRequestPayload>) {
      const { received = [], assets = [], ...collection } = await fetchExchangeSavings(payload);
      set(exchangeAssets, assets);
      set(exchangeReceived, received);
      return collection;
    }

    beforeEach(() => {
      set(mainPage, true);
      set(exchangeAssets, []);
      set(exchangeReceived, []);
    });

    it('initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >(fetchSavings, {
        history: get(mainPage) ? 'router' : false,
        locationOverview: exchange,
        defaultParams,
        defaultSortBy: [{
          direction: 'asc',
        }],
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual(undefined);
      expect(get(sort)).toHaveLength(1);
      expect(get(sort)).toMatchObject([
        {
          column: 'timestamp',
          direction: 'asc',
        },
      ]);
      expect(get(state).data).toHaveLength(0);
      expect(get(exchangeAssets)).toHaveLength(0);
      expect(get(exchangeReceived)).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      await nextTick();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toEqual(260);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >(fetchExchangeSavings, {
        history: get(mainPage) ? 'router' : false,
        locationOverview: exchange,
        defaultParams,
        defaultSortBy: [{
          direction: 'asc',
        }],
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<ExchangeSavingsEvent>>();
      expectTypeOf(get(state).data).toEqualTypeOf<ExchangeSavingsEvent[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
      expectTypeOf(get(matchers)).toEqualTypeOf<undefined[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortOrder: ['desc'] };

      const { isLoading, state, sort } = usePaginationFilters<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >(fetchSavings, {
        history: get(mainPage) ? 'router' : false,
        locationOverview: exchange,
        defaultParams,
        defaultSortBy: [{
          direction: 'asc',
        }],
      });

      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'asc',
      }]);

      await router.push({
        query,
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(get(route).query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<ExchangeSavingsEvent>>(get(state));
      assertType<ExchangeSavingsEvent[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(exchangeAssets)).toHaveLength(2);
      expect(get(exchangeReceived)).toHaveLength(2);
      expect(get(state).found).toEqual(260);
      expect(get(state).total).toEqual(260);
      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'desc',
      }]);
    });
  });
});
