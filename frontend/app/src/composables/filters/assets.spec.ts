import type { SupportedAsset } from '@rotki/common';
import type { MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { AssetRequestPayload } from '@/modules/assets/types';
import type { Collection } from '@/modules/common/collection';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { type Filters, type Matcher, useAssetFilter } from '@/composables/filters/assets';
import { usePaginationFilters } from '@/composables/use-pagination-filter';

vi.mock('vue', async () => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void) => fn()),
  };
});

describe('useAssetsFilter', () => {
  let fetchAssets: (payload: MaybeRef<AssetRequestPayload>) => Promise<Collection<SupportedAsset>>;
  const locationOverview = ref<string>('');
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

    const assetTypes = ref(['evm token', 'solana token']);

    it('should initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        Filters,
        Matcher
      >(fetchAssets, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useAssetFilter(assetTypes),
        locationOverview,
        defaultSortBy: [{
          column: 'symbol',
          direction: 'asc',
        }],
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).toStrictEqual({});
      expect(get(sort)).toStrictEqual([{
        column: 'symbol',
        direction: 'asc',
      }]);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toBe(0);

      set(userAction, true);
      await nextTick();
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toBe(210);
    });

    it('should return correct types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        Filters,
        Matcher
      >(fetchAssets, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useAssetFilter(assetTypes),
        locationOverview,
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<SupportedAsset>>();
      expectTypeOf(get(state).data).toEqualTypeOf<SupportedAsset[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['category'], sortOrder: ['desc'] };

      const { isLoading, state, sort } = usePaginationFilters<
        SupportedAsset,
        AssetRequestPayload,
        Filters,
        Matcher
      >(fetchAssets, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useAssetFilter(assetTypes),
        locationOverview,
        defaultSortBy: [{
          column: 'symbol',
          direction: 'asc',
        }],
      });

      expect(get(sort)).toStrictEqual([{
        column: 'symbol',
        direction: 'asc',
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

      assertType<Collection<SupportedAsset>>(get(state));
      assertType<SupportedAsset[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(state).found).toBe(210);
      expect(get(state).limit).toBe(-1);
      expect(get(state).total).toBe(210);

      expect(get(sort)).toStrictEqual([{
        column: 'category',
        direction: 'desc',
      }]);
    });
  });
});
