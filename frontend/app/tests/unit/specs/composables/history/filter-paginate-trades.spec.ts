import type { Collection } from '@/types/collection';
import type { TradeEntry, TradeRequestPayload } from '@/types/history/trade';
import type { LocationQuery } from '@/types/route';
import type { MaybeRef } from '@vueuse/core';
import type * as Vue from 'vue';
import { type Filters, type Matcher, useTradeFilters } from '@/composables/filters/trades';
import { useTrades } from '@/composables/history/trades';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';

vi.mock('vue-router', async () => {
  const { ref } = await import('vue');
  const { set } = await import('@vueuse/core');
  const route = ref({
    query: ref({}),
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
  let fetchTrades: (payload: MaybeRef<TradeRequestPayload>) => Promise<Collection<TradeEntry>>;
  const locationOverview = ref<string>('');
  const mainPage = ref<boolean>(false);
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
      includeIgnoredTrades: (!get(hideIgnoredTrades)).toString(),
    }));

    const onUpdateFilters = (query: LocationQuery) => {
      set(hideIgnoredTrades, query.includeIgnoredTrades === 'false');
    };

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        TradeEntry,
        TradeRequestPayload,
        Filters,
        Matcher
      >(fetchTrades, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useTradeFilters,
        locationOverview,
        onUpdateFilters,
        extraParams,
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'desc',
      });
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      await nextTick();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(210);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        TradeEntry,
        TradeRequestPayload,
        Filters,
        Matcher
      >(fetchTrades, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useTradeFilters,
        locationOverview,
        onUpdateFilters,
        extraParams,
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<TradeEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<TradeEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['type'], sortOrder: ['asc'] };

      const { isLoading, state, sort } = usePaginationFilters<
        TradeEntry,
        TradeRequestPayload,
        Filters,
        Matcher
      >(fetchTrades, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useTradeFilters,
        locationOverview,
        onUpdateFilters,
        extraParams,
      });

      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'desc',
      });

      await router.push({
        query,
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(get(route).query).toEqual(query);
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
      expect(get(sort)).toStrictEqual({
        column: 'type',
        direction: 'asc',
      });
    });

    it('handles pagination correctly when limit is less than total', async () => {
      const mockResponse: Collection<TradeEntry> = {
        data: new Array(10).fill({}),
        found: 300,
        limit: 100,
        total: 100,
      };

      const mockFetchTrades = vi.fn().mockResolvedValue(mockResponse);

      const { state, pagination, fetchData } = usePaginationFilters<
        TradeEntry,
        TradeRequestPayload,
        Filters,
        Matcher
      >(mockFetchTrades, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useTradeFilters,
        locationOverview,
        onUpdateFilters,
        extraParams,
      });

      await fetchData();
      await flushPromises();

      expect(get(state).found).toBe(300);
      expect(get(state).limit).toBe(100);
      expect(get(pagination).total).toBe(100);
    });
  });
});
