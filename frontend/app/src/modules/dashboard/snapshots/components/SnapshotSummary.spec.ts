import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotSummary from '@/modules/dashboard/snapshots/components/SnapshotSummary.vue';

const TIMESTAMP = 1_600_000_000;

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): { isUsd: Ref<boolean>; rate: Ref<BigNumber> } => ({
    isUsd: ref(true),
    rate: ref(One),
  }),
}));

function balance(assetIdentifier: string, usdValue: number, category: BalanceType = BalanceType.ASSET): BalanceSnapshot {
  return { amount: bigNumberify(1), assetIdentifier, category, timestamp: TIMESTAMP, usdValue: bigNumberify(usdValue) };
}

function location(name: string, usdValue: number): LocationDataSnapshot {
  return { location: name, timestamp: TIMESTAMP, usdValue: bigNumberify(usdValue) };
}

function snapshot(balances: BalanceSnapshot[], locations: LocationDataSnapshot[]): Snapshot {
  return { balancesSnapshot: balances, locationDataSnapshot: locations };
}

function mountSummary(props: Record<string, unknown> = {}): VueWrapper {
  return mount(SnapshotSummary, {
    global: {
      plugins: [createPinia()],
      provide: libraryDefaults,
      stubs: {
        AmountInput: { emits: ['update:modelValue'], props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
        DateDisplay: true,
        LocationDisplay: true,
        LocationSelector: true,
        SnapshotFiatDisplay: true,
        SnapshotFxOverrideControl: true,
      },
    },
    props: {
      snapshot: snapshot([balance('ETH', 100)], [location('total', 100)]),
      timestamp: TIMESTAMP,
      ...props,
    },
  });
}

describe('snapshotSummary', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should derive and show the net worth from the snapshot', () => {
    expect(mountSummary().find('[data-testid=snapshot-summary-net-worth]').exists()).toBe(true);
  });

  it('should show the delta only with a previous snapshot', () => {
    expect(mountSummary().find('[data-testid=snapshot-summary-delta]').exists()).toBe(false);
    const wrapper = mountSummary({ previous: { timestamp: TIMESTAMP - 86400, value: bigNumberify(80) } });
    expect(wrapper.find('[data-testid=snapshot-summary-delta]').exists()).toBe(true);
  });

  it('should show the allocation glance from the location rows', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100)], [location('kraken', 60), location('ledger', 40), location('total', 100)]) });
    expect(wrapper.find('[data-testid=snapshot-summary-allocation]').exists()).toBe(true);
  });

  it('should offer the exclude-NFTs toggle only when the snapshot has NFTs', () => {
    expect(mountSummary().find('[data-testid=snapshot-summary-exclude-nfts]').exists()).toBe(false);
    const withNft = snapshot([balance('_nft_0xabc_1', 40)], [location('total', 40)]);
    expect(mountSummary({ snapshot: withNft }).find('[data-testid=snapshot-summary-exclude-nfts]').exists()).toBe(true);
  });

  it('should show the reconcile alert when a mismatch is provided', () => {
    const wrapper = mountSummary({ mismatch: { balancesSum: bigNumberify(100), locationsSum: bigNumberify(90), storedTotal: bigNumberify(100) } });
    expect(wrapper.find('[data-testid=snapshot-summary-reconcile]').exists()).toBe(true);
    // The stored total can no longer be set to the locations sum.
    expect(wrapper.find('[data-testid=snapshot-summary-use-locations]').exists()).toBe(false);
  });

  it('should preselect no reconcile location and apply only once one is picked', async () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100)], [location('blockchain', 60), location('kraken', 20), location('total', 80)]),
      mismatch: { balancesSum: bigNumberify(100), locationsSum: bigNumberify(80), storedTotal: bigNumberify(80) },
    });
    const apply = wrapper.find('[data-testid=snapshot-summary-reconcile-apply]');

    expect(wrapper.findComponent(LocationSelector).props('modelValue')).toBe('');
    expect(apply.attributes('disabled')).toBeDefined();

    wrapper.findComponent(LocationSelector).vm.$emit('update:modelValue', 'kraken');
    await nextTick();
    await apply.trigger('click');

    expect(wrapper.emitted<[string]>('reconcile-locations')![0][0]).toBe('kraken');
  });

  it('should clear the reconcile location when navigating to another snapshot', async () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100)], [location('kraken', 60), location('ledger', 20), location('total', 80)]),
      mismatch: { balancesSum: bigNumberify(100), locationsSum: bigNumberify(80), storedTotal: bigNumberify(80) },
    });
    wrapper.findComponent(LocationSelector).vm.$emit('update:modelValue', 'ledger');

    // The page changes the route timestamp first and swaps the draft once the next snapshot loads.
    await wrapper.setProps({ timestamp: TIMESTAMP + 86400 });
    await wrapper.setProps({
      snapshot: snapshot([balance('BTC', 500)], [location('binance', 300), location('coinbase', 100), location('total', 400)]),
      mismatch: { balancesSum: bigNumberify(500), locationsSum: bigNumberify(400), storedTotal: bigNumberify(400) },
    });

    expect(wrapper.findComponent(LocationSelector).props('modelValue')).toBe('');
    expect(wrapper.find('[data-testid=snapshot-summary-reconcile-apply]').attributes('disabled')).toBeDefined();
  });

  it('should keep the chosen reconcile location while the same snapshot is edited', async () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100)], [location('kraken', 60), location('ledger', 20), location('total', 80)]),
      mismatch: { balancesSum: bigNumberify(100), locationsSum: bigNumberify(80), storedTotal: bigNumberify(80) },
    });
    wrapper.findComponent(LocationSelector).vm.$emit('update:modelValue', 'ledger');

    await wrapper.setProps({
      snapshot: snapshot([balance('ETH', 100)], [location('kraken', 70), location('ledger', 20), location('total', 90)]),
    });
    await wrapper.find('[data-testid=snapshot-summary-reconcile-apply]').trigger('click');

    expect(wrapper.emitted<[string]>('reconcile-locations')![0][0]).toBe('ledger');
  });

  it('should collapse zero-value rows into a single summary line', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 0), balance('DAI', 0)], [location('total', 0)]) });
    const warnings = wrapper.find('[data-testid=snapshot-summary-warnings]');
    expect(warnings.exists()).toBe(true);
    // The mocked t() renders `key::<count>`; the real string pluralizes the count.
    expect(warnings.text()).toContain('warnings.zero_value::2');
    // The individual asset names are not listed for zero-value rows.
    expect(warnings.text()).not.toContain('ETH');
  });

  it('should offer an action that isolates the zero-value rows', async () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 0), balance('DAI', 0)], [location('total', 0)]) });
    await wrapper.find('[data-testid=snapshot-summary-show-zero-value]').trigger('click');
    expect(wrapper.emitted('show-zero-value')).toHaveLength(1);
  });

  it('should not offer the isolate action without zero-value rows', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', -5)], [location('total', -5)]) });
    // The negative-balance warning is shown, but it names its own asset.
    expect(wrapper.find('[data-testid=snapshot-summary-warnings]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=snapshot-summary-show-zero-value]').exists()).toBe(false);
  });

  it('should list a genuine sanity warning with its asset', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', -5)], [location('total', -5)]) });
    const warnings = wrapper.find('[data-testid=snapshot-summary-warnings]');
    expect(warnings.exists()).toBe(true);
    expect(warnings.text()).toContain('ETH');
  });
});
