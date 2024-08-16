import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import type { Filters, Matcher } from '@/composables/filters/assets';
import type { Collection } from '@/types/collection';
import type { SupportedAsset } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type Vue from 'vue';
import type { AssetRequestPayload } from '@/types/asset';

vi.mock('vue-router', () => ({
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
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: Function) => fn()),
  };
});

describe('composables::assets/filter-paginate', () => {
  let fetchAssets: (payload: MaybeRef<AssetRequestPayload>) => Promise<Collection<SupportedAsset>>;
  const locationOverview = ref<string | null>('');
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchAssets = useAssetManagementApi().queryAllAssets;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('default', () => {
    set(locationOverview, '');

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, applyRouteFilter, isLoading } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        SupportedAsset,
        Collection<SupportedAsset>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useAssetFilter, fetchAssets, {
        defaultSortBy: {
          key: 'symbol',
          ascending: [true],
        },
      });

      expect(get(userAction)).toBe(true);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(Array.isArray(get(sort))).toBe(false);
      expect(get(sort)).toMatchObject({
        column: 'symbol',
        direction: 'asc',
      });
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(210);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        SupportedAsset,
        Collection<SupportedAsset>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useAssetFilter, fetchAssets);

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<SupportedAsset>>();
      expectTypeOf(get(state).data).toEqualTypeOf<SupportedAsset[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['category'], sortDesc: ['true'] };

      const { isLoading, state } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        SupportedAsset,
        Collection<SupportedAsset>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useAssetFilter, fetchAssets);

      await router.push({
        query,
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<SupportedAsset>>(get(state));
      assertType<SupportedAsset[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).found).toEqual(210);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(210);
    });
  });
});
