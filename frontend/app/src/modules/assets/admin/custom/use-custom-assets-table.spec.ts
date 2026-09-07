import type { CustomAsset } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useCustomAssetsTable } from './use-custom-assets-table';

let collection: Ref<Collection<CustomAsset>>;

const {
  deleteCustomAsset,
  getCustomAssetTypes,
  queryAllCustomAssets,
  refetch,
  setMessage,
} = vi.hoisted(() => ({
  deleteCustomAsset: vi.fn(async () => Promise.resolve(true)),
  getCustomAssetTypes: vi.fn(),
  queryAllCustomAssets: vi.fn(),
  refetch: vi.fn(async () => Promise.resolve()),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: (): Record<string, unknown> => ({
    deleteCustomAsset,
    getCustomAssetTypes,
    queryAllCustomAssets,
  }),
}));

vi.mock('@/modules/assets/admin/custom/use-custom-asset-fields', () => ({
  useCustomAssetFields: (): Record<string, unknown> => ({}),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (main: boolean): unknown => (main ? { mode: 'route' } : undefined),
  useServerTable: (): Record<string, unknown> => ({
    collection,
    filter: ref({}),
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch,
    sort: ref([]),
  }),
}));

function asset(overrides: Partial<CustomAsset> = {}): CustomAsset {
  return {
    customAssetType: 'real estate',
    identifier: 'custom-1',
    name: 'A house',
    notes: '',
    ...overrides,
  };
}

function page(data: CustomAsset[]): Collection<CustomAsset> {
  return { data, found: data.length, limit: -1, total: data.length, totalValue: undefined };
}

let scope: ReturnType<typeof effectScope>;

function table(): ReturnType<typeof useCustomAssetsTable> {
  scope = effectScope();
  return scope.run(() => useCustomAssetsTable({ mainPage: true }))!;
}

describe('modules/assets/admin/custom/useCustomAssetsTable', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    collection = ref<Collection<CustomAsset>>(page([]));
    getCustomAssetTypes.mockResolvedValue(['real estate', 'art']);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('refreshing', () => {
    it('should read the page and the types together', async () => {
      const { refresh } = table();
      await refresh();

      expect(refetch).toHaveBeenCalledOnce();
      expect(getCustomAssetTypes).toHaveBeenCalledOnce();
    });

    it('should offer the types the form can choose from', async () => {
      const { refresh, types } = table();
      await refresh();

      expect(get(types)).toEqual(['real estate', 'art']);
    });
  });

  describe('deleting an asset', () => {
    it('should delete nothing until the dialog is confirmed', () => {
      const { showDeleteConfirmation } = table();
      showDeleteConfirmation(asset({ identifier: 'custom-5' }));

      expect(get(useConfirmStore().visible)).toBe(true);
      expect(deleteCustomAsset).not.toHaveBeenCalled();
    });

    it('should delete exactly the asset the dialog named, then refresh', async () => {
      const { showDeleteConfirmation } = table();
      showDeleteConfirmation(asset({ identifier: 'custom-5' }));
      await useConfirmStore().confirm();
      await flushPromises();

      expect(deleteCustomAsset).toHaveBeenCalledWith('custom-5');
      expect(deleteCustomAsset).toHaveBeenCalledOnce();
      expect(refetch).toHaveBeenCalledOnce();
      expect(getCustomAssetTypes).toHaveBeenCalledOnce();
    });

    it('should name the asset in the confirmation', () => {
      const { showDeleteConfirmation } = table();
      showDeleteConfirmation(asset({ name: 'A house' }));

      expect(get(useConfirmStore().confirmation).message)
        .toBe('asset_management.confirm_delete.message::A house');
    });

    it('should report a failed delete against the asset it tried', async () => {
      deleteCustomAsset.mockRejectedValue(new Error('still referenced'));

      const { showDeleteConfirmation } = table();
      showDeleteConfirmation(asset({ identifier: 'custom-5' }));
      await useConfirmStore().confirm();
      await flushPromises();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: expect.stringContaining('custom-5'),
      }));
    });

    it('should delete nothing when the dialog is dismissed', async () => {
      const { showDeleteConfirmation } = table();
      showDeleteConfirmation(asset());
      await useConfirmStore().dismiss();
      await flushPromises();

      expect(deleteCustomAsset).not.toHaveBeenCalled();
    });
  });
});
