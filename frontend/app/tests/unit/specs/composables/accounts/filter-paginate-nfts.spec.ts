import type { MaybeRef } from '@vueuse/core';
import type * as Vue from 'vue';
import type { Collection } from '@/types/collection';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import type { LocationQuery } from '@/types/route';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';

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
  let fetchNonFungibleBalances: (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ) => Promise<Collection<NonFungibleBalance>>;
  const locationOverview = ref<string>('');
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchNonFungibleBalances = useNftBalances().fetchNonFungibleBalances;
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
        isLoading,
      } = usePaginationFilters<NonFungibleBalance>(fetchNonFungibleBalances, {
        history: get(mainPage) ? 'router' : false,
        locationOverview,
        onUpdateFilters,
        extraParams,
        defaultSortBy: [{
          column: 'name',
          direction: 'asc',
        }],
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toHaveLength(1);
      expect(get(sort)).toMatchObject([{
        column: 'name',
        direction: 'asc',
      }]);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      await nextTick();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(30);
    });

    it('check the return types', () => {
      const {
        isLoading,
        state,
        filters,
        matchers,
      } = usePaginationFilters<NonFungibleBalance>(fetchNonFungibleBalances, {
        history: get(mainPage) ? 'router' : false,
        locationOverview,
        onUpdateFilters,
        extraParams,
        defaultSortBy: [
          {
            column: 'name',
            direction: 'asc',
          },
        ],
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<NonFungibleBalance>>();
      expectTypeOf(get(state).data).toEqualTypeOf<NonFungibleBalance[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
      expectTypeOf(get(matchers)).toEqualTypeOf<undefined[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortOrder: ['asc'] };

      const {
        isLoading,
        state,
        sort,
      } = usePaginationFilters<NonFungibleBalance>(fetchNonFungibleBalances, {
        history: get(mainPage) ? 'router' : false,
        locationOverview,
        onUpdateFilters,
        extraParams,
        defaultSortBy: [{
          column: 'name',
          direction: 'desc',
        }],
      });

      expect(get(sort)).toStrictEqual([{
        column: 'name',
        direction: 'desc',
      }]);

      await router.push({
        query,
      });

      await nextTick();

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(get(route).query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<NonFungibleBalance>>(get(state));
      assertType<NonFungibleBalance[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(9);
      expect(get(state).found).toEqual(29);
      expect(get(state).total).toEqual(30);
      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'asc',
      }]);
    });
  });
});
