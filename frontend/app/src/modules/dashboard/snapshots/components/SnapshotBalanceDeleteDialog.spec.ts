import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotBalanceDeleteDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceDeleteDialog.vue';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

const TS = 1_600_000_000;

function createSnapshot(krakenValue = 100): Snapshot {
  return {
    balancesSnapshot: [
      { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(100) },
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TS, usdValue: bigNumberify(krakenValue) },
      { location: 'total', timestamp: TS, usdValue: bigNumberify(100) },
    ],
  };
}

describe('modules/dashboard/snapshots/components/SnapshotBalanceDeleteDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotBalanceDeleteDialog>>;

  function createWrapper(snapshot: Snapshot = createSnapshot()): VueWrapper<InstanceType<typeof SnapshotBalanceDeleteDialog>> {
    return mount(SnapshotBalanceDeleteDialog, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ConfirmDialog: { emits: ['confirm', 'cancel'], props: ['display', 'disabled'], template: '<div v-if="display" :data-disabled="disabled"><slot /></div>' },
          EditBalancesSnapshotLocationSelector: { emits: ['update:modelValue'], props: { disabledLocations: { default: () => [] }, modelValue: {} }, template: '<input class="loc" :value="modelValue" :data-disabled-locations="(disabledLocations || []).join(\',\')" @input="$emit(\'update:modelValue\', $event.target.value)">' },
          SnapshotLocationSplit: { emits: ['update:modelValue', 'update:valid'], name: 'SnapshotLocationSplit', props: ['modelValue', 'total', 'locations', 'maxPerLocation', 'timestamp', 'valid'], template: '<div class="split-stub" />' },
        },
      },
      props: { snapshot, timestamp: TS },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should emit the chosen single location on confirm', async () => {
    wrapper = createWrapper();
    wrapper.vm.open(0);
    await nextTick();

    await wrapper.find('.loc').setValue('kraken');
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');

    expect(wrapper.emitted('confirm')).toEqual([[{ index: 0, location: 'kraken' }]]);
  });

  it('should preselect the only location that can cover the removal', async () => {
    wrapper = createWrapper();
    wrapper.vm.open(0);
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('.loc').element.value).toBe('kraken');
  });

  it('should preselect the sole eligible location among several', async () => {
    // kraken (60) can't cover the 100 removal, but ledger (120) can — and it's the
    // only one that can, so it should be auto-selected despite there being two.
    const snapshot: Snapshot = {
      balancesSnapshot: [
        { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(100) },
      ],
      locationDataSnapshot: [
        { location: 'kraken', timestamp: TS, usdValue: bigNumberify(60) },
        { location: 'ledger', timestamp: TS, usdValue: bigNumberify(120) },
        { location: 'total', timestamp: TS, usdValue: bigNumberify(180) },
      ],
    };
    wrapper = createWrapper(snapshot);
    wrapper.vm.open(0);
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('.loc').element.value).toBe('ledger');
  });

  it('should disable a location that cannot absorb the removal and block confirm', async () => {
    // kraken only holds 40 but the balance is 100 — it can't cover the removal.
    wrapper = createWrapper(createSnapshot(40));
    wrapper.vm.open(0);
    await nextTick();

    // Not preselected (it would overdraw) and surfaced as disabled.
    expect(wrapper.find<HTMLInputElement>('.loc').element.value).toBe('');
    expect(wrapper.find('.loc').attributes('data-disabled-locations')).toBe('kraken');

    // Required but unset → confirm is a no-op.
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it('should require a location even when removing a worthless row', async () => {
    // Two venues so a single one isn't auto-preselected, and a zero-value row.
    const snapshot: Snapshot = {
      balancesSnapshot: [
        { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(0) },
      ],
      locationDataSnapshot: [
        { location: 'kraken', timestamp: TS, usdValue: bigNumberify(60) },
        { location: 'ledger', timestamp: TS, usdValue: bigNumberify(40) },
        { location: 'total', timestamp: TS, usdValue: bigNumberify(100) },
      ],
    };
    wrapper = createWrapper(snapshot);
    wrapper.vm.open(0);
    await nextTick();

    // Location is mandatory everywhere now — unset blocks confirm.
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toBeUndefined();

    // Once a venue is chosen the (zero) removal is attributed and emitted.
    await wrapper.find('.loc').setValue('ledger');
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toEqual([[{ index: 0, location: 'ledger' }]]);
  });

  it('should block confirm in split mode until the split is valid', async () => {
    wrapper = createWrapper();
    wrapper.vm.open(0);
    await nextTick();

    await wrapper.find('[data-testid=snapshot-balances-delete-split-toggle] input').setValue(true);
    await nextTick();

    // Invalid split — confirm is a no-op.
    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toBeUndefined();

    // Valid split is emitted.
    const split: LocationSplit[] = [{ location: 'kraken', usdValue: bigNumberify(100) }];
    wrapper.findComponent({ name: 'SnapshotLocationSplit' }).vm.$emit('update:modelValue', split);
    wrapper.findComponent({ name: 'SnapshotLocationSplit' }).vm.$emit('update:valid', true);
    await nextTick();

    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toEqual([[{ index: 0, location: split }]]);
  });
});
