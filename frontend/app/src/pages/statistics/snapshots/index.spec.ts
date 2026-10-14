import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import type { useSnapshotsPage } from '@/pages/statistics/snapshots/use-snapshots-page';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import SnapshotsPage from '@/pages/statistics/snapshots/index.vue';

const confirmDelete = vi.fn();
const exportSnapshot = vi.fn(async (): Promise<boolean> => true);
const importSnapshot = vi.fn();
const open = vi.fn();
const refresh = vi.fn(async (): Promise<void> => {});
const takeSnapshot = vi.fn(async (): Promise<void> => {});

interface PageState {
  rows: SnapshotListRow[];
}

const pageState = vi.hoisted((): PageState => ({ rows: [] }));

const ListTableStub = defineComponent({
  emits: ['open', 'export', 'delete', 'update:pagination'],
  name: 'SnapshotListTableStub',
  props: {
    emptyDescription: { default: '', type: String },
    exporting: { default: undefined, type: Number },
    loading: { default: false, type: Boolean },
    pagination: { default: undefined, type: Object },
    rows: { default: () => [], type: Array },
  },
  template: '<div data-testid="snapshot-list" />',
});

vi.mock('@/pages/statistics/snapshots/use-snapshots-page', async () => {
  const { computed, ref, shallowRef } = await import('vue');
  return {
    useSnapshotsPage: (): ReturnType<typeof useSnapshotsPage> => ({
      confirmDelete,
      emptyDescription: computed(() => 'nothing here'),
      exportSnapshot,
      exporting: shallowRef(undefined),
      forceSaving: shallowRef(false),
      importSnapshot,
      importing: shallowRef(false),
      loading: shallowRef(false),
      modelBalanceFile: shallowRef(undefined),
      modelFilters: ref({}),
      modelImportDialog: shallowRef(false),
      modelLocationFile: shallowRef(undefined),
      modelPagination: ref({ limit: 10, page: 1, total: 0 }),
      open,
      refresh,
      rows: computed(() => pageState.rows),
      takeSnapshot,
    }),
  };
});

describe('pages/statistics/snapshots/index', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotsPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof SnapshotsPage>> {
    return mount(SnapshotsPage, {
      attachTo: document.body,
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          SnapshotImportDialog: { props: ['modelValue', 'balanceFile', 'locationFile', 'loading'], template: '<div data-testid="import-dialog" />' },
          SnapshotListFilter: { props: ['modelValue'], template: '<div data-testid="list-filter" />' },
          SnapshotListTable: ListTableStub,
          TablePageLayout: { props: ['title'], template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  function confirmButton(): HTMLElement | null {
    return document.body.querySelector<HTMLElement>('[data-testid=take-snapshot-confirm-button]');
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.rows = [];
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
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

  it('should ask in a popover before taking a snapshot, and take it once confirmed', async () => {
    vi.useFakeTimers();
    try {
      wrapper = mountPage();

      await wrapper.find('[data-testid=take-snapshot]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();
      await flushPromises();

      expect(takeSnapshot).not.toHaveBeenCalled();
      expect(confirmButton()).not.toBeNull();

      confirmButton()?.click();
      await flushPromises();

      expect(takeSnapshot).toHaveBeenCalledTimes(1);
    }
    finally {
      vi.useRealTimers();
    }
  });

  it('should route each table event to its own handler, with the timestamp', () => {
    wrapper = mountPage();
    const table = wrapper.findComponent(ListTableStub);

    table.vm.$emit('open', 100);
    table.vm.$emit('export', 200);
    table.vm.$emit('delete', 300);

    expect(open).toHaveBeenCalledWith(100);
    expect(exportSnapshot).toHaveBeenCalledWith(200);
    expect(confirmDelete).toHaveBeenCalledWith(300);
  });

  it('should show the filter and the import dialog', () => {
    wrapper = mountPage();

    expect(wrapper.find('[data-testid=list-filter]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=import-dialog]').exists()).toBe(true);
  });
});
