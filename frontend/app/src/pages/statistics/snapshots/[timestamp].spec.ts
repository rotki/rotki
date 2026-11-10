import type { ActionStatus } from '@/modules/core/common/action';
import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import type { BalanceMutation } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, nextTick, type Ref, ref } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import SnapshotBalancesTable from '@/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue';
import SnapshotEditorToolbar from '@/modules/dashboard/snapshots/components/SnapshotEditorToolbar.vue';
import SnapshotSummary from '@/modules/dashboard/snapshots/components/SnapshotSummary.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import SnapshotDetailPage from '@/pages/statistics/snapshots/[timestamp].vue';

const TIMESTAMP = 1_600_000_000;
const NEXT_TIMESTAMP = 1_600_086_400;

function createSnapshot(): Snapshot {
  return {
    balancesSnapshot: [
      { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TIMESTAMP, usdValue: bigNumberify(100) },
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TIMESTAMP, usdValue: bigNumberify(100) },
      { location: 'total', timestamp: TIMESTAMP, usdValue: bigNumberify(100) },
    ],
  };
}

const fetchSnapshot = vi.fn(async (): Promise<Snapshot> => createSnapshot());
const persist = vi.fn(async (_timestamp: number, _snapshot: Snapshot): Promise<boolean> => true);
const remove = vi.fn(async (): Promise<boolean> => true);
const refreshNetValue = vi.fn(async (): Promise<void> => {});
const pushMock = vi.fn();
const markAssetsAsSpam = vi.fn(async (_assets: string[], _options?: { silent?: boolean }): Promise<ActionStatus> => ({ success: true }));

const route = vi.hoisted(() => ({ setTimestamp: (_value: number): void => {} }));

vi.mock('vue-router', async () => {
  const { computed, ref } = await import('vue');
  const current = ref<number>(1_600_000_000);
  route.setTimestamp = (value: number): void => {
    current.value = value;
  };
  return {
    onBeforeRouteLeave: vi.fn(),
    useRoute: (): ComputedRef<{ params: { timestamp: string } }> =>
      computed(() => ({ params: { timestamp: String(current.value) } })),
    useRouter: (): { push: typeof pushMock } => ({ push: pushMock }),
  };
});

vi.mock('@/modules/dashboard/snapshots/use-snapshot-store', () => ({
  useSnapshotStore: (): {
    fetchSnapshot: typeof fetchSnapshot;
    invalidate: () => void;
    persist: typeof persist;
    remove: typeof remove;
  } => ({ fetchSnapshot, invalidate: vi.fn(), persist, remove }),
}));

vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: (): { markAssetsAsSpam: typeof markAssetsAsSpam } => ({ markAssetsAsSpam }),
}));

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-list', () => ({
  useSnapshotList: (): { refresh: typeof refreshNetValue; rows: ComputedRef<SnapshotListRow[]> } => ({
    refresh: refreshNetValue,
    rows: computed(() => []),
  }),
}));

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): {
    isUsd: Ref<boolean>;
    loading: Ref<boolean>;
    rate: Ref<BigNumber>;
    rateReady: Ref<boolean>;
  } => ({
    isUsd: ref(true),
    loading: ref(false),
    rate: ref(One),
    rateReady: ref(true),
  }),
}));

const mutation: BalanceMutation = {
  balance: { amount: bigNumberify(2), assetIdentifier: 'BTC', category: BalanceType.ASSET, timestamp: TIMESTAMP, usdValue: bigNumberify(50) },
  location: 'kraken',
};

describe('pages/statistics/snapshots/[timestamp]', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotDetailPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof SnapshotDetailPage>> {
    return mount(SnapshotDetailPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ExportSnapshotDialog: true,
          SnapshotBalancesTable: { emits: ['add', 'edit', 'delete', 'bulk-delete'], props: ['snapshot', 'timestamp'], template: '<div data-testid="balances-stub" />' },
          SnapshotEditorToolbar: { emits: ['save', 'discard', 'undo', 'export', 'delete', 'navigate'], props: ['timestamp', 'changes', 'canUndo', 'saving', 'hasPrev', 'hasNext'], template: '<div data-testid="toolbar-stub" />' },
          SnapshotLocationsDrawer: { emits: ['add', 'edit', 'delete', 'distribute'], props: ['snapshot', 'timestamp', 'modelValue'], template: '<div data-testid="locations-stub" />' },
          SnapshotSummary: { props: ['snapshot', 'timestamp', 'previous', 'autoTrack', 'excludeNfts'], template: '<div data-testid="summary-stub" />' },
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    route.setTimestamp(TIMESTAMP);
    fetchSnapshot.mockClear();
    fetchSnapshot.mockImplementation(async (): Promise<Snapshot> => createSnapshot());
    persist.mockClear();
    persist.mockImplementation(async (): Promise<boolean> => true);
    remove.mockClear();
    remove.mockImplementation(async (): Promise<boolean> => true);
    refreshNetValue.mockClear();
    pushMock.mockClear();
    markAssetsAsSpam.mockClear();
    markAssetsAsSpam.mockImplementation(async (): Promise<ActionStatus> => ({ success: true }));
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should load the snapshot and show the stored net worth in the summary', async () => {
    wrapper = mountPage();
    await flushPromises();

    expect(fetchSnapshot).toHaveBeenCalledWith(TIMESTAMP);

    const summary = wrapper.findComponent(SnapshotSummary);
    expect(summary.exists()).toBe(true);
    const snapshot: Snapshot = summary.props('snapshot');
    expect(snapshot.locationDataSnapshot.find(item => item.location === 'total')?.usdValue.toNumber()).toBe(100);
    expect(wrapper.findComponent(SnapshotEditorToolbar).props('changes')).toEqual([]);
  });

  it('should become dirty when a panel emits an op', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('add', mutation);
    await flushPromises();

    const toolbar = wrapper.findComponent(SnapshotEditorToolbar);
    expect(toolbar.props('changes').length).toBeGreaterThan(0);
  });

  it('should persist the draft when the toolbar emits save', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('add', mutation);
    await flushPromises();

    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('save');
    await flushPromises();

    expect(persist).toHaveBeenCalledTimes(1);
    expect(persist.mock.calls[0][0]).toBe(TIMESTAMP);
  });

  it('should re-pull the net-value series after a successful save', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('add', mutation);
    await flushPromises();

    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('save');
    await flushPromises();

    expect(refreshNetValue).toHaveBeenCalledTimes(1);
  });

  it('should not touch the net-value series when the save is rejected', async () => {
    persist.mockResolvedValue(false);
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('add', mutation);
    await flushPromises();

    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('save');
    await flushPromises();

    expect(refreshNetValue).not.toHaveBeenCalled();
  });

  it('should sweep the flagged balances straight away, leaving the draft undoable', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('bulk-delete', [0]);
    await flushPromises();

    expect(useConfirmStore().visible).toBe(false);
    const toolbar = wrapper.findComponent(SnapshotEditorToolbar);
    expect(toolbar.props('canUndo')).toBe(true);
  });

  it('should delete on the toolbar\'s already-confirmed delete, re-pulling the net-value series before leaving', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('delete');
    await flushPromises();

    expect(remove).toHaveBeenCalledWith(TIMESTAMP);
    expect(refreshNetValue).toHaveBeenCalledTimes(1);
    expect(pushMock).toHaveBeenCalledWith('/statistics/snapshots');
    expect(refreshNetValue.mock.invocationCallOrder[0]).toBeLessThan(pushMock.mock.invocationCallOrder[0]);
  });

  it('should keep the loaded snapshot on screen while navigating to another one', async () => {
    wrapper = mountPage();
    await flushPromises();
    expect(wrapper.findComponent(ProgressScreen).exists()).toBe(false);

    let resolveNext: (snapshot: Snapshot) => void = () => {};
    fetchSnapshot.mockImplementation(async (): Promise<Snapshot> => new Promise((resolve) => {
      resolveNext = resolve;
    }));

    route.setTimestamp(NEXT_TIMESTAMP);
    await nextTick();
    await nextTick();

    expect(fetchSnapshot).toHaveBeenLastCalledWith(NEXT_TIMESTAMP);
    expect(wrapper.findComponent(ProgressScreen).exists()).toBe(false);
    expect(wrapper.findComponent(SnapshotSummary).exists()).toBe(true);

    resolveNext(createSnapshot());
    await flushPromises();
  });

  it('should mark the asset of a row deleted as spam once the snapshot is saved', async () => {
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('delete', { index: 0, location: 'kraken', markSpam: true });
    await flushPromises();
    expect(wrapper.findComponent(SnapshotEditorToolbar).props('changes')).toContainEqual({ asset: 'ETH', kind: 'spam-marked' });

    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('save');
    await flushPromises();

    expect(markAssetsAsSpam).toHaveBeenCalledExactlyOnceWith(['ETH'], { silent: true });
    expect(persist.mock.invocationCallOrder[0]).toBeLessThan(markAssetsAsSpam.mock.invocationCallOrder[0]);
    expect(wrapper.find('[data-testid=snapshot-save-success]').exists()).toBe(true);
    expect(wrapper.findComponent(SnapshotEditorToolbar).props('changes')).toEqual([]);
  });

  it('should report a failed spam mark while keeping it pending for the next save', async () => {
    markAssetsAsSpam.mockResolvedValue({ message: 'backend down', success: false });
    wrapper = mountPage();
    await flushPromises();

    wrapper.findComponent(SnapshotBalancesTable).vm.$emit('delete', { index: 0, location: 'kraken', markSpam: true });
    wrapper.findComponent(SnapshotEditorToolbar).vm.$emit('save');
    await flushPromises();

    expect(persist).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid=snapshot-action-error]').text()).toContain('spam_failure::backend down');
    expect(wrapper.findComponent(SnapshotEditorToolbar).props('changes')).toEqual([{ asset: 'ETH', kind: 'spam-marked' }]);
    expect(refreshNetValue).toHaveBeenCalledOnce();
  });
});
