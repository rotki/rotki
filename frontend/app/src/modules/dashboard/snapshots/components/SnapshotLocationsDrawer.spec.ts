import type { LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import type { LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotLocationEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotLocationEntryDialog.vue';
import SnapshotLocationsDrawer from '@/modules/dashboard/snapshots/components/SnapshotLocationsDrawer.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): { isUsd: Ref<boolean>; rate: Ref<BigNumber> } => ({
    isUsd: ref(true),
    rate: ref(One),
  }),
}));

const TS = 1_600_000_000;

function createSnapshot(locationsSum = 100): Snapshot {
  return {
    balancesSnapshot: [
      { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(100) },
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TS, usdValue: bigNumberify(locationsSum) },
      { location: 'total', timestamp: TS, usdValue: bigNumberify(100) },
    ],
  };
}

const newLocation: LocationDataSnapshot = { location: 'binance', timestamp: TS, usdValue: bigNumberify(40) };

describe('modules/dashboard/snapshots/components/SnapshotLocationsDrawer', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotLocationsDrawer>>;

  function createWrapper(snapshot: Snapshot = createSnapshot()): VueWrapper<InstanceType<typeof SnapshotLocationsDrawer>> {
    return mount(SnapshotLocationsDrawer, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        // The drawer teleports its content; stub it to render the slot inline.
        stubs: {
          RuiNavigationDrawer: { template: '<div><slot /></div>' },
        },
      },
      props: { modelValue: true, snapshot, timestamp: TS },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('USD') });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should render only the non-total location rows', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-locations-drawer]').exists()).toBe(true);
    expect(wrapper.text()).toContain('100.00');
  });

  it('should map a dialog add submit to the add event', () => {
    wrapper = createWrapper();

    wrapper.findComponent(SnapshotLocationEntryDialog).vm.$emit('submit', { index: null, location: newLocation });

    expect(wrapper.emitted('add')).toEqual([[newLocation]]);
  });

  it('should map a dialog edit submit to the edit event', () => {
    wrapper = createWrapper();

    wrapper.findComponent(SnapshotLocationEntryDialog).vm.$emit('submit', { index: 0, location: newLocation });

    expect(wrapper.emitted('edit')).toEqual([[{ index: 0, location: newLocation }]]);
  });

  it('should not show the reconcile alert when the sums match', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-locations-reconcile]').exists()).toBe(false);
  });

  it('should confirm a balanced allocation when the sums match', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-locations-balanced]').exists()).toBe(true);
  });

  it('should hide the balanced confirmation when the allocation is off', () => {
    wrapper = createWrapper(createSnapshot(60));

    expect(wrapper.find('[data-testid=snapshot-locations-balanced]').exists()).toBe(false);
  });

  it('should emit distribute with the split when the allocation is reconciled', async () => {
    wrapper = createWrapper(createSnapshot(60));

    expect(wrapper.find('[data-testid=snapshot-locations-reconcile]').exists()).toBe(true);

    await wrapper.find('[data-testid=snapshot-locations-distribute]').trigger('click');

    const split: LocationSplit[] = [
      { location: 'kraken', usdValue: bigNumberify(70) },
      { location: 'binance', usdValue: bigNumberify(30) },
    ];
    const splitComponent = wrapper.findComponent(SnapshotLocationSplit);
    splitComponent.vm.$emit('update:modelValue', split);
    splitComponent.vm.$emit('update:valid', true);
    await nextTick();

    await wrapper.find('[data-testid=snapshot-locations-distribute-apply]').trigger('click');

    expect(wrapper.emitted('distribute')).toEqual([[split]]);
  });
});
