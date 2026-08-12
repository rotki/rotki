import type { SupportedAsset } from '@rotki/common';
import type { MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { Filters } from '@/modules/assets/admin/managed/use-assets-filter';
import type { AssetRequestPayload } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { useServerTable } from '@/modules/core/table/use-server-table';

vi.mock('vue', async () => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void) => fn()),
  };
});

describe('useAssetsFilter', () => {
  let fetchAssets: (payload: MaybeRef<AssetRequestPayload>) => Promise<Collection<SupportedAsset>>;
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();

  beforeEach(async () => {
    // Fresh pinia per test plus a reset of the shared vue-router mock route ref. The mock's
    // route query is a module-level singleton that useRouter().push mutates, so the query set
    // by the "modify filters" test would otherwise leak into whichever test runs next under
    // shuffle and override the default sort. A fresh useRouter() has its own push mock, so
    // this reset does not inflate any push-spy the tests assert on.
    setActivePinia(createPinia());
    fetchAssets = useAssetManagementApi().queryAllAssets;
    await useRouter().push({ query: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('default', () => {
    beforeEach(() => {
      set(mainPage, true);
    });

    it('should initialize composable correctly', async () => {
      const { markUserIntent, filter, sort, collection, refetch, isLoading } = useServerTable<
        SupportedAsset,
        AssetRequestPayload,
        Filters
      >({
        fetch: fetchAssets,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        sort: {
          default: [{
            column: 'symbol',
            direction: 'asc',
          }],
        },
      });
      expect(get(isLoading)).toBe(false);
      expect(get(filter)).toStrictEqual({});
      expect(get(sort)).toStrictEqual([{
        column: 'symbol',
        direction: 'asc',
      }]);
      expect(get(collection).data).toHaveLength(0);
      expect(get(collection).total).toBe(0);
      markUserIntent();
      await nextTick();
      startPromise(refetch());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(collection).total).toBe(210);
    });

    it('should return correct types', () => {
      const { isLoading, collection, filter } = useServerTable<
        SupportedAsset,
        AssetRequestPayload,
        Filters
      >({
        fetch: fetchAssets,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(collection)).toEqualTypeOf<Collection<SupportedAsset>>();
      expectTypeOf(get(collection).data).toEqualTypeOf<SupportedAsset[]>();
      expectTypeOf(get(collection).found).toEqualTypeOf<number>();
      expectTypeOf(get(filter)).toEqualTypeOf<Filters>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['category'], sortOrder: ['desc'] };

      const { isLoading, collection, sort } = useServerTable<
        SupportedAsset,
        AssetRequestPayload,
        Filters
      >({
        fetch: fetchAssets,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        sort: {
          default: [{
            column: 'symbol',
            direction: 'asc',
          }],
        },
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

      assertType<Collection<SupportedAsset>>(get(collection));
      assertType<SupportedAsset[]>(get(collection).data);
      assertType<number>(get(collection).found);

      expect(get(collection).data).toHaveLength(10);
      expect(get(collection).found).toBe(210);
      expect(get(collection).limit).toBe(-1);
      expect(get(collection).total).toBe(210);

      expect(get(sort)).toStrictEqual([{
        column: 'category',
        direction: 'desc',
      }]);
    });
  });
});
