import type { CexMapping } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import ManageCexMappingContent from '@/modules/assets/admin/cex-mapping/ManageCexMappingContent.vue';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import ManageCexMappingTable from '@/modules/assets/admin/cex-mapping/ManageCexMappingTable.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface RouteHolder {
  route?: Ref<{ query: Record<string, string> }>;
}

let filter: Ref<Record<string, string | string[] | undefined>>;

const { deleteCexMapping, fetchAllCexMapping, held, refetch, replace } = vi.hoisted(() => {
  const held: RouteHolder = {};
  return {
    deleteCexMapping: vi.fn(async () => Promise.resolve(true)),
    fetchAllCexMapping: vi.fn(),
    held,
    refetch: vi.fn(async () => Promise.resolve()),
    replace: vi.fn(async () => Promise.resolve()),
  };
});

vi.mock('vue-router', async () => {
  const { ref: actualRef } = await vi.importActual<typeof import('vue')>('vue');
  held.route = actualRef({ query: {} });
  return {
    useRoute: (): unknown => held.route,
    useRouter: (): Record<string, unknown> => ({ replace }),
  };
});

vi.mock('@/modules/assets/api/use-asset-cex-mapping-api', () => ({
  useAssetCexMappingApi: (): Record<string, unknown> => ({ deleteCexMapping, fetchAllCexMapping }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): Record<string, unknown> => ({
    collection: ref<Collection<CexMapping>>({ data: [], found: 0, limit: -1, total: 0, totalValue: undefined }),
    filter,
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch,
  }),
}));

const MAPPING: CexMapping = { asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' };

function createWrapper(): VueWrapper {
  return mount(ManageCexMappingContent, {
    global: {
      plugins: [createCustomPinia()],
      stubs: {
        ManageCexMappingFormDialog: true,
        ManageCexMappingTable: true,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
  });
}

describe('modules/assets/admin/cex-mapping/ManageCexMappingContent.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filter = ref<Record<string, string | string[] | undefined>>({});
    held.route = ref({ query: {} });
  });

  it('should read the mappings when it opens', async () => {
    createWrapper();
    await flushPromises();

    expect(refetch).toHaveBeenCalledOnce();
  });

  it('should open the dialog on a blank mapping from the add button', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=managed-cex-mapping-add-btn]').trigger('click');

    expect(wrapper.findComponent(ManageCexMappingFormDialog).props('modelValue'))
      .toEqual({ asset: '', location: '', locationSymbol: '' });
  });

  it('should seed the new mapping from the filter', async () => {
    set(filter, { location: 'kraken', locationSymbol: 'XBT' });

    const wrapper = createWrapper();
    await flushPromises();
    await wrapper.find('[data-testid=managed-cex-mapping-add-btn]').trigger('click');

    expect(wrapper.findComponent(ManageCexMappingFormDialog).props('modelValue'))
      .toEqual({ asset: '', location: 'kraken', locationSymbol: 'XBT' });
  });

  it('should hand the table a row to edit straight to the dialog', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCexMappingTable).vm.$emit('edit', MAPPING);
    await flushPromises();

    const dialog = wrapper.findComponent(ManageCexMappingFormDialog);
    expect(dialog.props('modelValue')).toEqual(MAPPING);
    expect(dialog.props('editMode')).toBe(true);
  });

  it('should ask before deleting a row the table asked to remove', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCexMappingTable).vm.$emit('delete', MAPPING);
    await flushPromises();

    expect(get(useConfirmStore().visible)).toBe(true);
    expect(deleteCexMapping).not.toHaveBeenCalled();
  });

  it('should delete the row once the dialog is confirmed, without its asset', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCexMappingTable).vm.$emit('delete', MAPPING);
    await useConfirmStore().confirm();
    await flushPromises();

    expect(deleteCexMapping).toHaveBeenCalledWith({ location: 'kraken', locationSymbol: 'XBT' });
  });

  it('should open the dialog seeded from an ?add= link', async () => {
    held.route = ref({ query: { add: 'true', location: 'coinbase', locationSymbol: 'ETH' } });

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.findComponent(ManageCexMappingFormDialog).props('modelValue'))
      .toEqual({ asset: '', location: 'coinbase', locationSymbol: 'ETH' });
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });
});
