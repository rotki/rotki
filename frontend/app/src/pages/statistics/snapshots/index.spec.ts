import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import type { useSnapshotsPage } from '@/pages/statistics/snapshots/use-snapshots-page';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import SnapshotsPage from '@/pages/statistics/snapshots/index.vue';

const confirmDelete = vi.fn();
const confirmTakeSnapshot = vi.fn();
const importSnapshot = vi.fn();
const open = vi.fn();
const openExport = vi.fn();
const refresh = vi.fn(async (): Promise<void> => {});

interface PageState {
  rows: SnapshotListRow[];
  selectedTimestamp: number;
}

const pageState = vi.hoisted((): PageState => ({ rows: [], selectedTimestamp: 0 }));

const ListTableStub = defineComponent({
  emits: ['open', 'export', 'delete', 'update:pagination'],
  name: 'SnapshotListTableStub',
  props: {
    emptyDescription: { default: '', type: String },
    loading: { default: false, type: Boolean },
    pagination: { default: undefined, type: Object },
    rows: { default: () => [], type: Array },
  },
  template: '<div data-testid="snapshot-list" />',
});

const ExportDialogStub = defineComponent({
  name: 'ExportSnapshotDialogStub',
  props: {
    balance: { default: undefined, type: Object },
    modelValue: { default: false, type: Boolean },
    timestamp: { default: 0, type: Number },
  },
  template: '<div data-testid="export-dialog" />',
});

vi.mock('@/pages/statistics/snapshots/use-snapshots-page', async () => {
  const { computed, ref, shallowRef } = await import('vue');
  return {
    useSnapshotsPage: (): ReturnType<typeof useSnapshotsPage> => ({
      confirmDelete,
      confirmTakeSnapshot,
      emptyDescription: computed(() => 'nothing here'),
      forceSaving: shallowRef(false),
      importSnapshot,
      importing: shallowRef(false),
      loading: shallowRef(false),
      modelBalanceFile: shallowRef(undefined),
      modelExportDialog: shallowRef(false),
      modelFilters: ref({}),
      modelImportDialog: shallowRef(false),
      modelLocationFile: shallowRef(undefined),
      modelPagination: ref({ limit: 10, page: 1, total: 0 }),
      open,
      openExport,
      refresh,
      rows: computed(() => pageState.rows),
      selectedBalance: computed(() => bigNumberify(500)),
      selectedTimestamp: computed(() => pageState.selectedTimestamp),
    }),
  };
});

describe('pages/statistics/snapshots/index', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotsPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof SnapshotsPage>> {
    return mount(SnapshotsPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ExportSnapshotDialog: ExportDialogStub,
          SnapshotImportDialog: { props: ['modelValue', 'balanceFile', 'locationFile', 'loading'], template: '<div data-testid="import-dialog" />' },
          SnapshotListFilter: { props: ['modelValue'], template: '<div data-testid="list-filter" />' },
          SnapshotListTable: ListTableStub,
          TablePageLayout: { props: ['title'], template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.rows = [];
    pageState.selectedTimestamp = 0;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should hand the rows and the empty message to the table', () => {
    pageState.rows = [{ timestamp: 100, usdValue: bigNumberify(500) }];

    wrapper = mountPage();

    const table = wrapper.findComponent(ListTableStub);
    expect(table.props('rows')).toHaveLength(1);
    expect(table.props('emptyDescription')).toBe('nothing here');
  });

  it('should refresh from the toolbar button', async () => {
    wrapper = mountPage();

    await wrapper.find('[data-testid=refresh-snapshots]').trigger('click');

    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it('should ask before taking a snapshot rather than taking one', async () => {
    wrapper = mountPage();

    await wrapper.find('[data-testid=take-snapshot]').trigger('click');

    expect(confirmTakeSnapshot).toHaveBeenCalledTimes(1);
  });

  it('should route each table event to its own handler, with the timestamp', () => {
    wrapper = mountPage();
    const table = wrapper.findComponent(ListTableStub);

    table.vm.$emit('open', 100);
    table.vm.$emit('export', 200);
    table.vm.$emit('delete', 300);

    expect(open).toHaveBeenCalledWith(100);
    expect(openExport).toHaveBeenCalledWith(200);
    expect(confirmDelete).toHaveBeenCalledWith(300);
  });

  it('should hand the selected snapshot and its value to the export dialog', () => {
    pageState.selectedTimestamp = 200;

    wrapper = mountPage();

    const dialog = wrapper.findComponent(ExportDialogStub);
    expect(dialog.props('timestamp')).toBe(200);
    expect(dialog.props('balance')).toStrictEqual(bigNumberify(500));
  });

  it('should show the filter and the import dialog', () => {
    wrapper = mountPage();

    expect(wrapper.find('[data-testid=list-filter]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=import-dialog]').exists()).toBe(true);
  });
});
