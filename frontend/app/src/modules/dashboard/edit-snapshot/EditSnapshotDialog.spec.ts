import type { LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import EditSnapshotDialog from '@/modules/dashboard/edit-snapshot/EditSnapshotDialog.vue';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: vi.fn(),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn().mockReturnValue({
    fetchNetValue: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>(
    '@/modules/core/notifications/use-notifications',
  );
  return {
    ...actual,
    useNotifications: vi.fn(),
  };
});

const BalancesTableStub = defineComponent({
  emits: ['update:model-value', 'update:step'],
  name: 'EditBalancesSnapshotTable',
  props: ['modelValue', 'timestamp'],
  render() {
    return h('div', { class: 'balances-stub' });
  },
});

const LocationTableStub = defineComponent({
  emits: ['update:model-value', 'update:step'],
  name: 'EditLocationDataSnapshotTable',
  props: ['modelValue', 'timestamp'],
  render() {
    return h('div', { class: 'location-stub' });
  },
});

const TotalStub = defineComponent({
  emits: ['update:model-value', 'update:step'],
  name: 'EditSnapshotTotal',
  props: ['modelValue', 'balancesSnapshot', 'timestamp'],
  render() {
    return h('div', { class: 'total-stub' });
  },
});

type DialogInstance = InstanceType<typeof EditSnapshotDialog>;

describe('edit-snapshot/EditSnapshotDialog.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<DialogInstance>;

  let getSnapshotData: ReturnType<typeof vi.fn<ReturnType<typeof useSnapshotApi>['getSnapshotData']>>;
  let updateSnapshotData: ReturnType<typeof vi.fn<ReturnType<typeof useSnapshotApi>['updateSnapshotData']>>;
  let fetchNetValue: ReturnType<typeof vi.fn<ReturnType<typeof useStatisticsDataFetching>['fetchNetValue']>>;
  let notifyError: ReturnType<typeof vi.fn<ReturnType<typeof useNotifications>['notifyError']>>;
  let showSuccessMessage: ReturnType<typeof vi.fn<ReturnType<typeof useNotifications>['showSuccessMessage']>>;

  const timestamp = 1700000000;

  function fixtureSnapshot(): Snapshot {
    return {
      balancesSnapshot: [
        {
          amount: bigNumberify('1.5'),
          assetIdentifier: 'ETH',
          category: BalanceType.ASSET,
          timestamp,
          usdValue: bigNumberify('3000'),
        },
        {
          amount: bigNumberify('0.1'),
          assetIdentifier: 'BTC',
          category: BalanceType.ASSET,
          timestamp,
          usdValue: bigNumberify('4000'),
        },
      ],
      locationDataSnapshot: [
        { location: 'blockchain', timestamp, usdValue: bigNumberify('5000') },
        { location: 'total', timestamp, usdValue: bigNumberify('7000') },
      ],
    };
  }

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    getSnapshotData = vi.fn<ReturnType<typeof useSnapshotApi>['getSnapshotData']>().mockResolvedValue(fixtureSnapshot());
    updateSnapshotData = vi.fn<ReturnType<typeof useSnapshotApi>['updateSnapshotData']>().mockResolvedValue(true);
    fetchNetValue = vi.fn<ReturnType<typeof useStatisticsDataFetching>['fetchNetValue']>().mockResolvedValue(undefined);
    notifyError = vi.fn<ReturnType<typeof useNotifications>['notifyError']>();
    showSuccessMessage = vi.fn<ReturnType<typeof useNotifications>['showSuccessMessage']>();

    vi.mocked(useSnapshotApi).mockReturnValue({
      deleteSnapshot: vi.fn(),
      downloadSnapshot: vi.fn(),
      exportSnapshotCSV: vi.fn(),
      getSnapshotData,
      importBalancesSnapshot: vi.fn(),
      updateSnapshotData,
      uploadBalancesSnapshot: vi.fn(),
    });

    vi.mocked(useStatisticsDataFetching).mockReturnValue({
      fetchNetValue,
    });

    vi.mocked(useNotifications).mockReturnValue({
      notify: vi.fn(),
      notifyError,
      notifyInfo: vi.fn(),
      notifyWarning: vi.fn(),
      removeMatching: vi.fn(),
      showErrorMessage: vi.fn(),
      showSuccessMessage,
    });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(): VueWrapper<DialogInstance> {
    return mount(EditSnapshotDialog, {
      attachTo: document.body,
      global: {
        plugins: [pinia],
        stubs: {
          EditBalancesSnapshotTable: BalancesTableStub,
          EditLocationDataSnapshotTable: LocationTableStub,
          EditSnapshotTotal: TotalStub,
        },
      },
      props: { timestamp },
    });
  }

  it('should fetch the snapshot on mount', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(getSnapshotData).toHaveBeenCalledWith(timestamp);
    expect(wrapper.findComponent(BalancesTableStub).exists()).toBe(true);
  });

  it('should sort balances and locations descending by usdValue', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const passed: Snapshot = wrapper.findComponent(BalancesTableStub).props('modelValue');
    expect(passed.balancesSnapshot.map(b => b.assetIdentifier)).toEqual(['BTC', 'ETH']);
    expect(passed.locationDataSnapshot.map(l => l.location)).toEqual(['total', 'blockchain']);
  });

  it('should call updateSnapshotData with both arrays when balances stub emits update:model-value', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const next: Snapshot = {
      balancesSnapshot: [{
        amount: bigNumberify('2'),
        assetIdentifier: 'ETH',
        category: BalanceType.ASSET,
        timestamp,
        usdValue: bigNumberify('4000'),
      }],
      locationDataSnapshot: [
        { location: 'blockchain', timestamp, usdValue: bigNumberify('5000') },
      ],
    };

    const balances = wrapper.findComponent(BalancesTableStub);
    balances.vm.$emit('update:model-value', next);
    await flushPromises();

    expect(updateSnapshotData).toHaveBeenCalledTimes(1);
    expect(updateSnapshotData).toHaveBeenCalledWith(timestamp, {
      balancesSnapshot: [{
        amount: '2',
        assetIdentifier: 'ETH',
        category: BalanceType.ASSET,
        timestamp,
        usdValue: '4000',
      }],
      locationDataSnapshot: [
        { location: 'blockchain', timestamp, usdValue: '5000' },
      ],
    });
  });

  it('should call updateSnapshotData once per balances stub emit', async () => {
    wrapper = createWrapper();
    await flushPromises();

    const next: Snapshot = {
      balancesSnapshot: [{
        amount: bigNumberify('2'),
        assetIdentifier: 'ETH',
        category: BalanceType.ASSET,
        timestamp,
        usdValue: bigNumberify('4000'),
      }],
      locationDataSnapshot: [
        { location: 'blockchain', timestamp, usdValue: bigNumberify('5000') },
      ],
    };

    const balances = wrapper.findComponent(BalancesTableStub);
    balances.vm.$emit('update:model-value', next);
    balances.vm.$emit('update:model-value', next);
    await flushPromises();

    expect(updateSnapshotData).toHaveBeenCalledTimes(2);
  });

  it('should call updateSnapshotData with merged payload when location stub emits', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(BalancesTableStub).vm.$emit('update:step', 2);
    await flushPromises();

    const newLocations: LocationDataSnapshot[] = [
      { location: 'blockchain', timestamp, usdValue: bigNumberify('9000') },
    ];

    const location = wrapper.findComponent(LocationTableStub);
    location.vm.$emit('update:model-value', newLocations);
    await flushPromises();

    expect(updateSnapshotData).toHaveBeenCalledTimes(1);
    const [, payload] = updateSnapshotData.mock.calls[0];
    expect(payload.balancesSnapshot.map((b: { assetIdentifier: string }) => b.assetIdentifier)).toEqual(['BTC', 'ETH']);
    expect(payload.locationDataSnapshot).toEqual([
      { location: 'blockchain', timestamp, usdValue: '9000' },
    ]);
  });

  it('should call updateSnapshotData and emit finish when total stub completes', async () => {
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(BalancesTableStub).vm.$emit('update:step', 3);
    await flushPromises();

    const total = wrapper.findComponent(TotalStub);
    total.vm.$emit('update:model-value', [
      { location: 'total', timestamp, usdValue: bigNumberify('7000') },
    ]);
    await flushPromises();

    expect(updateSnapshotData).toHaveBeenCalledTimes(1);
    expect(showSuccessMessage).toHaveBeenCalled();
    expect(fetchNetValue).toHaveBeenCalled();
    expect(wrapper.emitted('finish')).toBeTruthy();
  });

  it('should notify when updateSnapshotData resolves false on completion', async () => {
    updateSnapshotData.mockResolvedValueOnce(false);
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(BalancesTableStub).vm.$emit('update:step', 3);
    await flushPromises();

    const total = wrapper.findComponent(TotalStub);
    total.vm.$emit('update:model-value', [
      { location: 'total', timestamp, usdValue: bigNumberify('7000') },
    ]);
    await flushPromises();

    expect(notifyError).toHaveBeenCalled();
    expect(showSuccessMessage).not.toHaveBeenCalled();
    expect(wrapper.emitted('finish')).toBeFalsy();
  });

  it('should notify and not emit finish when updateSnapshotData throws on completion', async () => {
    updateSnapshotData.mockRejectedValueOnce(new Error('boom'));
    wrapper = createWrapper();
    await flushPromises();

    wrapper.findComponent(BalancesTableStub).vm.$emit('update:step', 3);
    await flushPromises();

    const total = wrapper.findComponent(TotalStub);
    total.vm.$emit('update:model-value', [
      { location: 'total', timestamp, usdValue: bigNumberify('7000') },
    ]);
    await flushPromises();

    expect(notifyError).toHaveBeenCalled();
    expect(showSuccessMessage).not.toHaveBeenCalled();
    expect(wrapper.emitted('finish')).toBeFalsy();
  });
});
