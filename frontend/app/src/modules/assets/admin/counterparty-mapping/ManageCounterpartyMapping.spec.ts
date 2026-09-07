import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { Collection } from '@/modules/core/common/collection';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import ManageCounterpartyMapping from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMapping.vue';
import ManageCounterpartyMappingFormDialog from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingFormDialog.vue';
import ManageCounterpartyMappingTable from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingTable.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface RouteHolder {
  route?: Ref<{ query: Record<string, string> }>;
}

let filter: Ref<Record<string, string | string[] | undefined>>;

const { deleteCounterpartyMapping, fetchAllCounterpartyMapping, held, refetch, replace } = vi.hoisted(() => {
  const held: RouteHolder = {};
  return {
    deleteCounterpartyMapping: vi.fn(async () => Promise.resolve(true)),
    fetchAllCounterpartyMapping: vi.fn(),
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

vi.mock('@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-api', () => ({
  useCounterpartyMappingApi: (): Record<string, unknown> => ({
    deleteCounterpartyMapping,
    fetchAllCounterpartyMapping,
  }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): Record<string, unknown> => ({
    collection: ref<Collection<CounterpartyMapping>>({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
      totalValue: undefined,
    }),
    filter,
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch,
  }),
}));

const MAPPING: CounterpartyMapping = { asset: 'ETH', counterparty: 'uniswap', counterpartySymbol: 'WETH' };

function createWrapper(): VueWrapper {
  return mount(ManageCounterpartyMapping, {
    global: {
      plugins: [createCustomPinia()],
      stubs: {
        ManageCounterpartyMappingFormDialog: true,
        ManageCounterpartyMappingTable: true,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
  });
}

describe('modules/assets/admin/counterparty-mapping/ManageCounterpartyMapping.vue', () => {
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

  it('should seed the new mapping from the filter', async () => {
    set(filter, { counterparty: 'uniswap', counterpartySymbol: 'WETH' });

    const wrapper = createWrapper();
    await flushPromises();
    await wrapper.find('[data-testid=managed-counterparty-mapping-add-btn]').trigger('click');

    expect(wrapper.findComponent(ManageCounterpartyMappingFormDialog).props('modelValue'))
      .toEqual({ asset: '', counterparty: 'uniswap', counterpartySymbol: 'WETH' });
  });

  it('should hand the table a row to edit straight to the dialog', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCounterpartyMappingTable).vm.$emit('edit', MAPPING);
    await flushPromises();

    const dialog = wrapper.findComponent(ManageCounterpartyMappingFormDialog);
    expect(dialog.props('modelValue')).toEqual(MAPPING);
    expect(dialog.props('editMode')).toBe(true);
  });

  it('should ask before deleting a row the table asked to remove', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCounterpartyMappingTable).vm.$emit('delete', MAPPING);
    await flushPromises();

    expect(get(useConfirmStore().visible)).toBe(true);
    expect(deleteCounterpartyMapping).not.toHaveBeenCalled();
  });

  it('should delete the row once the dialog is confirmed, without its asset', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(ManageCounterpartyMappingTable).vm.$emit('delete', MAPPING);
    await useConfirmStore().confirm();
    await flushPromises();

    expect(deleteCounterpartyMapping).toHaveBeenCalledWith({ counterparty: 'uniswap', counterpartySymbol: 'WETH' });
  });

  it('should open the dialog seeded from an ?add= link', async () => {
    held.route = ref({ query: { add: 'true', counterparty: 'curve', counterpartySymbol: 'CRV' } });

    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.findComponent(ManageCounterpartyMappingFormDialog).props('modelValue'))
      .toEqual({ asset: '', counterparty: 'curve', counterpartySymbol: 'CRV' });
    expect(replace).toHaveBeenCalledWith({ query: {} });
  });
});
