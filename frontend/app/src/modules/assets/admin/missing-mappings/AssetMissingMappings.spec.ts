import type { MissingMapping } from '@/modules/user-data/schemas';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import AssetMissingMappings from '@/modules/assets/admin/missing-mappings/AssetMissingMappings.vue';
import MissingMappingDismissButton from '@/modules/assets/admin/missing-mappings/MissingMappingDismissButton.vue';

const { load, onAddClick, onDismiss, row } = vi.hoisted(() => ({
  load: vi.fn<() => Promise<void>>(async () => {}),
  onAddClick: vi.fn<(item: MissingMapping) => void>(),
  onDismiss: vi.fn<(item: MissingMapping) => Promise<void>>(async () => {}),
  row: { details: 'balance query', id: 7, identifier: 'BTTC', location: 'binance', name: '' } satisfies MissingMapping,
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-asset-missing-mappings', async () => {
  const { ref } = await import('vue');
  return {
    useAssetMissingMappings: (): Record<string, unknown> => ({
      cols: ref([]),
      error: ref(),
      fields: [],
      load,
      mappings: ref({ data: [row], found: 1, limit: -1, total: 1 }),
      modelFilter: ref({}),
      modelMapping: ref(),
      onAddClick,
      onAddComplete: vi.fn(),
      onDismiss,
      pagination: ref({ limit: 10, page: 1, total: 1 }),
      sort: ref([]),
    }),
  };
});

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (): void => {},
}));

/** Renders only the actions cell of each row, which is where the row buttons are wired. */
const TableStub = defineComponent({
  props: ['rows'],
  template: `<div>
    <template v-for="row in rows" :key="row.id">
      <slot name="item.actions" :row="row" />
    </template>
  </div>`,
});

function createWrapper(): VueWrapper<InstanceType<typeof AssetMissingMappings>> {
  return mount(AssetMissingMappings, {
    global: {
      stubs: {
        AssetManagerMoreTitle: true,
        ManageCexMappingFormDialog: true,
        MissingMappingDismissButton: true,
        PillFilterBar: true,
        RuiDataTable: TableStub,
        TableFrame: { template: '<div><slot /></div>' },
        TablePageLayout: { template: '<div><slot /></div>' },
      },
    },
  });
}

describe('assetMissingMappings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should drop resolved rows and read the page when opened', async () => {
    createWrapper();
    await flushPromises();

    expect(load).toHaveBeenCalledOnce();
  });

  it('should dismiss the row whose dismiss button is clicked, without starting a mapping', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(MissingMappingDismissButton).vm.$emit('dismiss');
    await nextTick();

    expect(onDismiss).toHaveBeenCalledExactlyOnceWith(row);
    expect(onAddClick).not.toHaveBeenCalled();
  });

  it('should start a mapping for the row whose add button is clicked, without dismissing it', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid="row-add"]').trigger('click');

    expect(onAddClick).toHaveBeenCalledExactlyOnceWith(row);
    expect(onDismiss).not.toHaveBeenCalled();
  });
});
