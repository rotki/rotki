import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import type { Filters, Matcher } from '@/composables/filters/asset-movement';
import type { Collection } from '@/types/collection';
import type { AssetMovementEntry, AssetMovementRequestPayload } from '@/types/history/asset-movements';
import type { MaybeRef } from '@vueuse/core';
import type Vue from 'vue';

vi.mock('vue-router', () => {
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
  let fetchAssetMovements: (payload: MaybeRef<AssetMovementRequestPayload>) => Promise<Collection<AssetMovementEntry>>;
  const locationOverview = ref<string>('');
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchAssetMovements = useAssetMovements().fetchAssetMovements;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/DepositsWithdrawalsContent', () => {
    set(locationOverview, '');

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        AssetMovementEntry,
        AssetMovementRequestPayload,
        Filters,
        Matcher
      >(fetchAssetMovements, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useAssetMovementFilters,
        locationOverview,
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).toStrictEqual({});
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
      expect(get(state).total).toEqual(45);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        AssetMovementEntry,
        AssetMovementRequestPayload,
        Filters,
        Matcher
      >(fetchAssetMovements, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useAssetMovementFilters,
        locationOverview,
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<AssetMovementEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<AssetMovementEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['category'], sortOrder: ['desc'] };

      const { isLoading, state, sort } = usePaginationFilters<
        AssetMovementEntry,
        AssetMovementRequestPayload,
        Filters,
        Matcher
      >(fetchAssetMovements, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: useAssetMovementFilters,
        locationOverview,
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

      assertType<Collection<AssetMovementEntry>>(get(state));
      assertType<AssetMovementEntry[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).found).toEqual(45);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(45);
      expect(get(sort)).toStrictEqual({
        column: 'category',
        direction: 'desc',
      });
    });
  });
});
