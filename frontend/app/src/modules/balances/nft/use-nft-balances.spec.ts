import type { MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import type { LocationQuery } from '@/modules/core/table/route';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

describe('useNftBalances', () => {
  let fetchNonFungibleBalances: (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ) => Promise<Collection<NonFungibleBalance>>;
  const locationOverview = ref<string>('');
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll((): void => {
    setActivePinia(createPinia());
    fetchNonFungibleBalances = useNftBalances().fetchNonFungibleBalances;
  });

  afterEach((): void => {
    vi.clearAllMocks();
  });

  describe('components::accounts/balances/NonFungibleBalances.vue', () => {
    set(locationOverview, '');
    const ignoredAssetsHandling = ref('none');
    const extraParams = computed(() => ({
      includeIgnoredTrades: get(ignoredAssetsHandling),
    }));

    const onUpdateFilters = (query: LocationQuery): void => {
      set(ignoredAssetsHandling, query.includeIgnoredTrades);
    };

    beforeEach((): void => {
      set(mainPage, true);
    });

    it('should initialize composable correctly', async () => {
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
      expect(get(state).total).toBe(0);

      set(userAction, true);
      await nextTick();
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toBe(30);
    });

    it('should return correct types', () => {
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

    it('should modify filters and fetch data correctly', async () => {
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
      expect(get(state).found).toBe(29);
      expect(get(state).total).toBe(30);
      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'asc',
      }]);
    });
  });
});
