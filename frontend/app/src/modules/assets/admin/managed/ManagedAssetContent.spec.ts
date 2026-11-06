import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ManagedAssetContent from '@/modules/assets/admin/managed/ManagedAssetContent.vue';

const { assetTypesFailure, loadAssetTypes, refetch } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    assetTypesFailure: shallowRef<unknown>(),
    loadAssetTypes: vi.fn<() => Promise<void>>(),
    refetch: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): unknown => ({ value: { query: {} } }),
  useRouter: (): Record<string, unknown> => ({ replace: vi.fn() }),
}));

vi.mock('@/modules/core/common/use-add-query', () => ({
  useAddQuery: (): Record<string, unknown> => ({ consumeAddQuery: vi.fn(async () => false) }),
}));

vi.mock('@/modules/assets/admin/managed/use-managed-asset-form', async () => {
  const { ref } = await import('vue');
  return {
    useManagedAssetForm: (): Record<string, unknown> => ({
      add: vi.fn(),
      assetTypes: ref<string[]>([]),
      assetTypesFailure,
      edit: vi.fn(),
      editAsset: vi.fn(),
      editMode: ref<boolean>(false),
      loadAssetTypes,
      modelValue: ref(),
    }),
  };
});

vi.mock('@/modules/assets/admin/managed/use-managed-assets-table', async () => {
  const { ref } = await import('vue');
  return {
    useManagedAssetsTable: (): Record<string, unknown> => ({
      assets: ref({ data: [], found: 0, limit: -1, total: 0 }),
      deleteAsset: vi.fn(),
      deleteConfirm: ref(),
      deleteFailure: ref(),
      fields: ref([]),
      loading: ref<boolean>(false),
      modelExpanded: ref([]),
      modelFilter: ref({}),
      modelIgnoredAssetsHandling: ref('none'),
      modelPillParams: ref({}),
      modelSelectedRows: ref([]),
      pagination: ref({ limit: 10, page: 1, total: 0 }),
      refetch,
      sort: ref([]),
    }),
  };
});

function createWrapper(): VueWrapper {
  return mount(ManagedAssetContent, {
    global: {
      plugins: [createCustomPinia()],
      stubs: {
        ManagedAssetFormDialog: true,
        ManagedAssetTable: true,
        MergeDialog: true,
        RestoreAssetDbButton: true,
        TablePageLayout: { template: '<div><slot /></div>' },
      },
    },
  });
}

describe('managedAssetContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    assetTypesFailure.value = undefined;
    refetch.mockResolvedValue(undefined);
    loadAssetTypes.mockResolvedValue(undefined);
  });

  it('should name an asset types load failure and retry it from the strip', async () => {
    assetTypesFailure.value = new Error('offline');
    const wrapper = createWrapper();
    await flushPromises();

    const strip = wrapper.find('[data-testid=managed-asset-types-error]');
    expect(strip.text()).toContain('asset_form.types.load_failed');
    expect(strip.text()).toContain('offline');

    await strip.find('[data-testid=failure-strip-retry]').trigger('click');

    expect(loadAssetTypes).toHaveBeenCalledOnce();
  });

  it('should show no strip when the asset types loaded', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=managed-asset-types-error]').exists()).toBe(false);
  });
});
