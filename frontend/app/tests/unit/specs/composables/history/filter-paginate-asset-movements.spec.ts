import flushPromises from 'flush-promises';
import { type Ref } from 'vue';
import type { Filters, Matcher } from '@/composables/filters/asset-movement';
import type { Collection } from '@/types/collection';
import type {
  AssetMovement,
  AssetMovementEntry,
  AssetMovementRequestPayload
} from '@/types/history/movements';
import type { MaybeRef } from '@vueuse/core';
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
  let fetchAssetMovements: (
    payload: MaybeRef<AssetMovementRequestPayload>
  ) => Promise<Collection<AssetMovementEntry>>;
  const locationOverview: MaybeRef<string | null> = ref('');
  const mainPage: Ref<boolean> = ref(false);
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
        AssetMovement,
        AssetMovementRequestPayload,
        AssetMovementEntry,
        Collection<AssetMovementEntry>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        useAssetMovementFilters,
        fetchAssetMovements
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
      expect(get(state).total).toEqual(45);
    });

    test('check the return types', async () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        AssetMovement,
        AssetMovementRequestPayload,
        AssetMovementEntry,
        Collection<AssetMovementEntry>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        useAssetMovementFilters,
        fetchAssetMovements
      );

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<AssetMovementEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<AssetMovementEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    test('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['category'], sortDesc: ['true'] };

      const { isLoading, state } = usePaginationFilters<
        AssetMovement,
        AssetMovementRequestPayload,
        AssetMovementEntry,
        Collection<AssetMovementEntry>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        useAssetMovementFilters,
        fetchAssetMovements
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

      assertType<Collection<AssetMovementEntry>>(get(state));
      assertType<AssetMovementEntry[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).found).toEqual(45);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(45);
    });
  });
});
