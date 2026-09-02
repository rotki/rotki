import type { SupportedAsset } from '@rotki/common';
import type { Collection } from '@/modules/core/common/collection';
import type { useServerTable } from '@/modules/core/table/use-server-table';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent, h, ref } from 'vue';
import { IgnoredAssetHandlingType } from '@/modules/assets/types';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useManagedAssetsTable } from './use-managed-assets-table';

type ServerTableOptions = Parameters<typeof useServerTable>[0];

const {
  collection,
  deleteAsset,
  deleteCacheKey,
  queryAllAssets,
  refetch,
  setPage,
  show,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    collection: ref<Collection<SupportedAsset>>({ data: [], found: 0, limit: -1, total: 0 }),
    deleteAsset: vi.fn(),
    deleteCacheKey: vi.fn(),
    queryAllAssets: vi.fn(),
    refetch: vi.fn(),
    setPage: vi.fn(),
    show: vi.fn(),
  };
});

let serverTableOptions: ServerTableOptions | undefined;
let fieldsArgs: { count: () => number; types: unknown } | undefined;

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: (): Record<string, unknown> => ({ deleteAsset, queryAllAssets }),
}));

vi.mock('@/modules/assets/use-asset-info-cache', () => ({
  useAssetInfoCache: (): Record<string, unknown> => ({ deleteCacheKey }),
}));

vi.mock('@/modules/assets/admin/managed/use-managed-asset-fields', () => ({
  useManagedAssetFields: (types: unknown, count: () => number): unknown[] => {
    fieldsArgs = { count, types };
    return [];
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/table/use-server-table', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-server-table')>(),
  useServerTable: (options: ServerTableOptions): Record<string, unknown> => {
    serverTableOptions = options;
    return {
      collection,
      filter: ref({}),
      isLoading: ref(false),
      pagination: computed(() => ({ limit: 10, page: 1, total: 0 })),
      refetch,
      setPage,
      sort: ref([]),
    };
  },
}));

const wrappers: VueWrapper[] = [];

function asset(identifier: string, symbol: string): SupportedAsset {
  return { identifier, isRebasing: false, symbol };
}

function mountTable(mainPage = true): ReturnType<typeof useManagedAssetsTable> {
  let captured: ReturnType<typeof useManagedAssetsTable> | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useManagedAssetsTable(() => mainPage, ['evm token']);
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  if (setupError)
    throw setupError;
  return captured!;
}

describe('modules/assets/admin/managed/useManagedAssetsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createCustomPinia());
    set(collection, { data: [], found: 0, limit: -1, total: 0 });
    deleteAsset.mockResolvedValue(true);
    serverTableOptions = undefined;
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('deleting an asset', () => {
    it('should delete nothing until the user accepts', () => {
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation(asset('eip155:1/erc20:0xdead', 'DEAD'));

      expect(show).toHaveBeenCalledOnce();
      expect(deleteAsset).not.toHaveBeenCalled();
    });

    it('should delete exactly the asset the row named once accepted', async () => {
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation(asset('eip155:1/erc20:0xdead', 'DEAD'));
      await show.mock.calls[0][1]();

      expect(deleteAsset).toHaveBeenCalledExactlyOnceWith('eip155:1/erc20:0xdead');
    });

    it('should name the asset in the confirmation, so the user sees what goes', () => {
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation(asset('eip155:1/erc20:0xdead', 'DEAD'));

      expect(show.mock.calls[0][0].message).toContain('DEAD');
    });

    it('should still confirm for an asset with no symbol, rather than rendering undefined', () => {
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation({ identifier: 'eip155:1/erc20:0xdead', isRebasing: false });

      expect(show.mock.calls[0][0].message).not.toContain('undefined');
    });

    it('should drop the deleted asset from the info cache, which would keep serving its name', async () => {
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation(asset('eip155:1/erc20:0xdead', 'DEAD'));
      await show.mock.calls[0][1]();

      expect(deleteCacheKey).toHaveBeenCalledExactlyOnceWith('eip155:1/erc20:0xdead');
      expect(refetch).toHaveBeenCalledOnce();
    });

    it('should not touch the cache when the delete failed, the asset still being there', async () => {
      deleteAsset.mockRejectedValue(new Error('in use'));
      const { showDeleteConfirmation } = mountTable();

      showDeleteConfirmation(asset('eip155:1/erc20:0xdead', 'DEAD'));
      await show.mock.calls[0][1]();

      expect(deleteCacheKey).not.toHaveBeenCalled();
    });
  });

  describe('the selection', () => {
    it('should report the selected rows as identifiers, which is what the table speaks', () => {
      set(collection, {
        data: [asset('ETH', 'ETH'), asset('BTC', 'BTC')],
        found: 2,
        limit: -1,
        total: 2,
      });
      const { modelSelectedRows } = mountTable();

      set(modelSelectedRows, ['ETH', 'BTC']);

      expect(get(modelSelectedRows)).toEqual(['ETH', 'BTC']);
    });

    it('should resolve an identifier back to the asset on the current page', () => {
      set(collection, { data: [asset('ETH', 'ETH')], found: 1, limit: -1, total: 1 });
      const { modelSelectedRows } = mountTable();

      set(modelSelectedRows, ['ETH']);

      expect(get(modelSelectedRows)).toEqual(['ETH']);
    });

    it('should start empty', () => {
      expect(get(mountTable().modelSelectedRows)).toEqual([]);
    });
  });

  describe('the table it configures', () => {
    it('should sort by symbol ascending before the user picks anything', () => {
      mountTable();

      expect(serverTableOptions?.sort).toEqual({ default: { column: 'symbol', direction: 'asc' } });
    });

    it('should sync to the url only when it owns the page', () => {
      mountTable(true);
      expect(serverTableOptions?.urlState).toEqual({ mode: 'route' });

      mountTable(false);
      expect(serverTableOptions?.urlState).toEqual({ mode: 'none' });
    });

    it('should hand the table the asset query rather than fetching itself', () => {
      mountTable();

      expect(serverTableOptions?.fetch).toBe(queryAllAssets);
      expect(queryAllAssets).not.toHaveBeenCalled();
    });

    it('should start by excluding ignored assets', () => {
      expect(get(mountTable().modelIgnoredAssetsHandling)).toBe(IgnoredAssetHandlingType.EXCLUDE);
    });

    it('should give the filter the asset types it was handed', () => {
      mountTable();

      expect(fieldsArgs?.types).toEqual(['evm token']);
    });

    it('should give the filter a live count of the ignored assets, not a snapshot', () => {
      mountTable();
      expect(fieldsArgs?.count()).toBe(0);

      set(storeToRefs(useAssetsStore()).ignoredAssets, ['ETH', 'BTC']);

      expect(fieldsArgs?.count()).toBe(2);
    });
  });

  describe('refetching', () => {
    it('should pass the refetch straight through', async () => {
      const { refetch: refetchFromTable } = mountTable();

      await refetchFromTable();

      expect(refetch).toHaveBeenCalledOnce();
    });

    it('should pass the page change straight through', () => {
      mountTable().setPage(3);

      expect(setPage).toHaveBeenCalledExactlyOnceWith(3);
    });
  });
});
