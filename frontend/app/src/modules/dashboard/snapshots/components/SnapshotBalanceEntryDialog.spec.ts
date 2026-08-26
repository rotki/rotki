import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { BalanceMutation } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotBalanceEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog.vue';

const TS = 1_600_000_000;

const mockConversion = {
  isUsd: ref<boolean>(true),
  loading: ref<boolean>(false),
  rate: ref<BigNumber>(One),
  rateReady: ref<boolean>(true),
};

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): { isUsd: Ref<boolean>; loading: Ref<boolean>; rate: Ref<BigNumber>; rateReady: Ref<boolean> } => mockConversion,
}));

function createSnapshot(): Snapshot {
  return {
    balancesSnapshot: [
      { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(100) },
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TS, usdValue: bigNumberify(100) },
      { location: 'total', timestamp: TS, usdValue: bigNumberify(100) },
    ],
  };
}

/** Stands in for the form, which owns the fields but not the parsing under test. */
const FormStub = {
  emits: ['update:modelValue', 'update:stateUpdated', 'update:asset'],
  methods: {
    submitPrice(): void {},
    validate(): boolean {
      return true;
    },
  },
  name: 'EditBalancesSnapshotForm',
  props: ['modelValue', 'edit', 'hideLocation', 'previewLocationBalance', 'disabledLocations', 'locations', 'timestamp', 'stateUpdated'],
  // The split toggle lives in this slot, so the stub has to render it.
  template: '<div><slot name="before-location" /></div>',
};

describe('modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotBalanceEntryDialog>>;

  /**
   * What the dialog threw out of a handler. Vue routes those into its error handler, so a save that
   * throws still emits nothing: without this, a test asserting "nothing was submitted" cannot tell
   * a clean refusal from a crash, and stays green against the code it is meant to catch.
   */
  const handlerErrors: unknown[] = [];

  function createWrapper(): VueWrapper<InstanceType<typeof SnapshotBalanceEntryDialog>> {
    return mount(SnapshotBalanceEntryDialog, {
      global: {
        config: {
          errorHandler: (error: unknown): void => {
            handlerErrors.push(error);
          },
        },
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          BigDialog: {
            emits: ['confirm', 'cancel'],
            props: ['display', 'title', 'action', 'loading', 'promptOnClose'],
            template: '<div v-if="display"><slot /><button data-testid="confirm" @click="$emit(\'confirm\')" /></div>',
          },
          ConfirmSnapshotConflictReplacementDialog: true,
          EditBalancesSnapshotForm: FormStub,
          SnapshotLocationSplit: {
            emits: ['update:modelValue', 'update:valid'],
            name: 'SnapshotLocationSplit',
            props: ['modelValue', 'valid', 'total', 'locations', 'maxPerLocation', 'timestamp'],
            template: '<div />',
          },
        },
      },
      props: { snapshot: createSnapshot(), timestamp: TS },
    });
  }

  /** Opens the add dialog and puts the given fields in the form's model. */
  async function openAddWith(amount: string, usdValue: string): Promise<void> {
    wrapper.vm.openAdd();
    await nextTick();

    const form = wrapper.findComponent({ name: 'EditBalancesSnapshotForm' });
    form.vm.$emit('update:modelValue', {
      amount,
      assetIdentifier: 'ETH',
      category: BalanceType.ASSET,
      location: 'kraken',
      timestamp: TS,
      usdValue,
    });
    await nextTick();
  }

  function submitted(): BalanceMutation[] {
    const events = wrapper.emitted<[{ index: number | null; mutation: BalanceMutation }]>('submit');
    return (events ?? []).map(([payload]) => payload.mutation);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    set(mockConversion.isUsd, true);
    set(mockConversion.rate, One);
    handlerErrors.length = 0;
    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should submit the entered amount and value', async () => {
    await openAddWith('2', '250');
    await wrapper.find('[data-testid=confirm]').trigger('click');

    const [mutation] = submitted();
    expect(mutation.balance.amount.toNumber()).toBe(2);
    expect(mutation.balance.usdValue.toNumber()).toBe(250);
  });

  it('should pre-fill an edit with the stored USD value, unconverted', async () => {
    set(mockConversion.isUsd, false);
    set(mockConversion.rate, bigNumberify(0.85));
    wrapper.unmount();
    wrapper = createWrapper();

    wrapper.vm.openEdit({ ...createSnapshot().balancesSnapshot[0], index: 0 });
    await nextTick();

    const model = wrapper.findComponent({ name: 'EditBalancesSnapshotForm' }).props('modelValue');
    expect(model.usdValue).toBe('100');
    expect(model.amount).toBe('1');
  });

  it.each([
    ['a cleared amount', '', '250'],
    ['a cleared value', '2', ''],
    ['a half-typed amount', '-', '250'],
    ['a half-typed value', '2', '1.2.3'],
  ])('should not submit %s', async (_label, amount, usdValue) => {
    await openAddWith(amount, usdValue);
    await wrapper.find('[data-testid=confirm]').trigger('click');

    expect(handlerErrors).toEqual([]);
    expect(submitted()).toEqual([]);
  });

  it('should attribute the balance to the split rows in split mode', async () => {
    await openAddWith('2', '250');
    await wrapper.find('[data-testid=snapshot-balance-split-toggle] input').setValue(true);

    const split = wrapper.findComponent({ name: 'SnapshotLocationSplit' });
    split.vm.$emit('update:modelValue', [{ location: 'kraken', usdValue: bigNumberify(250) }]);
    split.vm.$emit('update:valid', true);
    await nextTick();

    await wrapper.find('[data-testid=confirm]').trigger('click');

    const [mutation] = submitted();
    expect(mutation.location).toEqual([{ location: 'kraken', usdValue: bigNumberify(250) }]);
  });

  // The location preview and the overdrawn-location check read the same field on every keystroke,
  // where a throw takes the dialog down rather than surfacing as a bad number.
  it('should keep rendering while the value field holds no number', async () => {
    await openAddWith('2', '1.2.3');

    // Nothing readable was entered, so the location is previewed as unchanged.
    const preview = wrapper.findComponent({ name: 'EditBalancesSnapshotForm' }).props('previewLocationBalance');
    expect(preview.before.toNumber()).toBe(100);
    expect(preview.after.toNumber()).toBe(100);
    expect(wrapper.findComponent({ name: 'EditBalancesSnapshotForm' }).props('disabledLocations')).toEqual([]);
  });
});
