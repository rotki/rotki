import type { LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';

const TS = 1_600_000_000;

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): { isUsd: Ref<boolean>; rate: Ref<BigNumber> } => ({
    isUsd: ref(true),
    rate: ref(One),
  }),
}));

function mountSplit(total = 100, maxPerLocation?: Record<string, BigNumber>): VueWrapper {
  return mount(SnapshotLocationSplit, {
    global: {
      plugins: [createPinia()],
      provide: libraryDefaults,
      stubs: {
        AmountInput: { emits: ['update:modelValue'], props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
        LocationSelector: { emits: ['update:modelValue'], props: ['modelValue'], template: '<input class="loc" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
        SnapshotFiatDisplay: true,
      },
    },
    props: {
      locations: ['kraken', 'ledger'],
      maxPerLocation,
      modelValue: [],
      timestamp: TS,
      total: bigNumberify(total),
      valid: false,
    },
  });
}

describe('modules/dashboard/snapshots/components/SnapshotLocationSplit', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function isValid(wrapper: VueWrapper): boolean {
    return wrapper.find('[data-testid=snapshot-location-split-remaining]').classes().includes('text-rui-success');
  }

  function lastSplits(wrapper: VueWrapper): LocationSplit[] {
    return wrapper.emitted<[LocationSplit[]]>('update:modelValue')!.at(-1)![0];
  }

  it('should start invalid with empty rows', () => {
    const wrapper = mountSplit();
    expect(isValid(wrapper)).toBe(false);
  });

  it('should become valid and sum to the total once the rows are filled', async () => {
    const wrapper = mountSplit(100);
    const locations = wrapper.findAll('.loc');
    const amounts = wrapper.findAll('input:not(.loc)');

    await locations[0].setValue('kraken');
    await locations[1].setValue('ledger');
    await amounts[0].setValue('60');
    await amounts[1].setValue('40');

    expect(isValid(wrapper)).toBe(true);
    const splits = lastSplits(wrapper);
    expect(splits.reduce((sum, s) => sum.plus(s.usdValue), bigNumberify(0)).toNumber()).toBe(100);
  });

  it('should stay invalid when the split does not add up', async () => {
    const wrapper = mountSplit(100);
    const locations = wrapper.findAll('.loc');
    const amounts = wrapper.findAll('input:not(.loc)');

    await locations[0].setValue('kraken');
    await locations[1].setValue('ledger');
    await amounts[0].setValue('10');
    await amounts[1].setValue('10');

    // The first row absorbs the remainder, so the emitted sum is still exact, but
    // the entered values disagree with that remainder — invalid until reconciled.
    expect(lastSplits(wrapper).reduce((sum, s) => sum.plus(s.usdValue), bigNumberify(0)).toNumber()).toBe(100);
    expect(isValid(wrapper)).toBe(false);
  });

  it('should stay invalid when a row removes more than its location holds', async () => {
    // kraken only holds 50, but the first row tries to remove 60 from it.
    const wrapper = mountSplit(100, { kraken: bigNumberify(50), ledger: bigNumberify(80) });
    const locations = wrapper.findAll('.loc');
    const amounts = wrapper.findAll('input:not(.loc)');

    await locations[0].setValue('kraken');
    await locations[1].setValue('ledger');
    await amounts[0].setValue('60');
    await amounts[1].setValue('40');

    // Sums to 100 but kraken is over-drawn (after = -10), so the split is invalid.
    expect(isValid(wrapper)).toBe(false);
  });

  it('should be valid when every row stays within its location cap', async () => {
    const wrapper = mountSplit(100, { kraken: bigNumberify(80), ledger: bigNumberify(80) });
    const locations = wrapper.findAll('.loc');
    const amounts = wrapper.findAll('input:not(.loc)');

    await locations[0].setValue('kraken');
    await locations[1].setValue('ledger');
    await amounts[0].setValue('60');
    await amounts[1].setValue('40');

    expect(isValid(wrapper)).toBe(true);
  });
});
