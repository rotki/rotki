import type { CustomAsset } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import CustomAssetContent from './CustomAssetContent.vue';
import CustomAssetFormDialog from './CustomAssetFormDialog.vue';
import CustomAssetTable from './CustomAssetTable.vue';

let collection: Ref<Collection<CustomAsset>>;

const { getCustomAssetTypes, queryAllCustomAssets } = vi.hoisted(() => ({
  getCustomAssetTypes: vi.fn(),
  queryAllCustomAssets: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: (): Record<string, unknown> => ({
    deleteCustomAsset: vi.fn(),
    getCustomAssetTypes,
    queryAllCustomAssets,
  }),
}));

vi.mock('@/modules/assets/admin/custom/use-custom-asset-fields', () => ({
  // The real composable returns `FieldDef[]`; an object here reaches the table's Array prop.
  useCustomAssetFields: (): unknown[] => [],
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (): unknown => undefined,
  useServerTable: (): Record<string, unknown> => ({
    collection,
    filter: ref({}),
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch: vi.fn(async () => Promise.resolve()),
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

/**
 * `TablePageLayout` holds the table and the dialog in its default slot, which an auto-stub does not
 * render, so it needs a pass-through stub for either to exist.
 */
function mountContent(props: { identifier?: string } = {}): ReturnType<typeof shallowMount> {
  return shallowMount(CustomAssetContent, {
    global: {
      stubs: {
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
    props,
  });
}

describe('modules/assets/admin/custom/CustomAssetContent', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    getCustomAssetTypes.mockResolvedValue(['real estate']);
    collection = ref<Collection<CustomAsset>>(page([]));
  });

  it('should hand the loaded page to the dialog, so a routed identifier can be found', async () => {
    const wanted = asset({ identifier: 'custom-2', name: 'A boat' });
    set(collection, page([asset(), wanted]));

    const wrapper = mountContent({ identifier: 'custom-2' });
    await flushPromises();

    const dialog = wrapper.findComponent(CustomAssetFormDialog);
    expect(dialog.props('open')).toBe(true);
    expect(dialog.props('editableItem')).toEqual(wanted);
  });

  it('should leave the dialog closed when the route names no asset', async () => {
    set(collection, page([asset()]));

    const wrapper = mountContent();
    await flushPromises();

    expect(wrapper.findComponent(CustomAssetFormDialog).props('open')).toBe(false);
  });

  it('should render the loaded page in the table', async () => {
    set(collection, page([asset({ name: 'A house' })]));

    const wrapper = mountContent();
    await flushPromises();

    expect(wrapper.findComponent(CustomAssetTable).props('assets')).toEqual(get(collection).data);
  });
});
