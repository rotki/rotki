import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { BigNumber, bigNumberify, One } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import SnapshotSummary from '@/modules/dashboard/snapshots/components/SnapshotSummary.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const TIMESTAMP = 1_600_000_000;

let pinia: Pinia;
let ignoredIds: string[] = [];
vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters', () => ({
  useSnapshotAssetFilters: (): { isSpamAsset: (id: string) => boolean; isIgnoredAsset: (id: string) => boolean } => ({
    isIgnoredAsset: (id: string): boolean => ignoredIds.includes(id),
    isSpamAsset: (): boolean => false,
  }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { getAssetField: (id: string) => string } => ({
    getAssetField: (id: string): string => `${id}-symbol`,
  }),
}));

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

/** The USD value handed to the (stubbed) fiat display carrying `testId`. */
function fiatValue(wrapper: VueWrapper, testId: string): number | undefined {
  const display = wrapper.findAllComponents(SnapshotFiatDisplay).find(item => item.attributes('data-testid') === testId);
  const value: unknown = display?.props('value');
  return value instanceof BigNumber ? value.toNumber() : undefined;
}

function mountSummary(props: Record<string, unknown> = {}): VueWrapper {
  return mount(SnapshotSummary, {
    global: {
      plugins: [pinia],
      provide: libraryDefaults,
      stubs: {
        AmountInput: { emits: ['update:modelValue'], props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
        DateDisplay: true,
        I18nT: { template: '<div><slot name="amount" /><slot name="assets" /></div>' },
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
    pinia = createPinia();
    setActivePinia(pinia);
    ignoredIds = [];
  });

  it('should derive and show the net worth from the snapshot', () => {
    expect(mountSummary().find('[data-testid=snapshot-summary-net-worth]').exists()).toBe(true);
  });

  it('should headline the net worth the snapshot list shows, without ignored assets', () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1000)], [location('total', 1100)]) });

    expect(fiatValue(wrapper, 'snapshot-summary-net-worth')).toBe(100);
    expect(fiatValue(wrapper, 'snapshot-summary-excluded-ignored')).toBe(1000);
  });

  it('should leave NFTs out of the headline when net value excludes them', () => {
    useSettingsRepo().updateFrontend({ nftsInNetValue: false });
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100), balance('_nft_0xabc_1', 40)], [location('total', 140)]) });

    expect(fiatValue(wrapper, 'snapshot-summary-net-worth')).toBe(100);
    expect(fiatValue(wrapper, 'snapshot-summary-excluded-nfts')).toBe(40);
  });

  it('should count NFTs in the headline by default', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100), balance('_nft_0xabc_1', 40)], [location('total', 140)]) });

    expect(fiatValue(wrapper, 'snapshot-summary-net-worth')).toBe(140);
    expect(wrapper.find('[data-testid=snapshot-summary-excluded-nfts]').exists()).toBe(false);
  });

  it('should not mention ignored assets when the snapshot has none', () => {
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100)], [location('total', 100)]) });

    expect(fiatValue(wrapper, 'snapshot-summary-net-worth')).toBe(100);
    expect(wrapper.find('[data-testid=snapshot-summary-excluded-ignored]').exists()).toBe(false);
  });

  it('should measure the delta between the values the snapshot list shows', () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({
      previous: { timestamp: TIMESTAMP - 86400, value: bigNumberify(80) },
      snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1000)], [location('total', 1100)]),
    });

    expect(fiatValue(wrapper, 'snapshot-summary-delta-value')).toBe(20);
    expect(wrapper.find('[data-testid=snapshot-summary-warnings]').exists()).toBe(false);
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

  it('should offer to remove the ignored rows when the locations were lowered to leave only their value out', async () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1e30), balance('BTC', 50)], [location('blockchain', 150), location('total', 1e30)]),
      mismatch: { balancesSum: bigNumberify(1e30).plus(150), locationsSum: bigNumberify(150), storedTotal: bigNumberify(1e30).plus(150) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-gap-assets]').text()).toBe('SPAM-symbol');
    await wrapper.find('[data-testid=snapshot-summary-remove-gap-rows]').trigger('click');

    expect(wrapper.emitted<[number[]]>('remove-balances')![0][0]).toEqual([1]);
  });

  it('should offer to remove the one row that makes up the whole mismatch when it is not spam', async () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100), balance('SHIB', 1e30)], [location('blockchain', 100), location('total', 100)]),
      mismatch: { balancesSum: bigNumberify(1e30).plus(100), locationsSum: bigNumberify(100), storedTotal: bigNumberify(1e30).plus(100) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-gap-assets]').text()).toBe('SHIB-symbol');
    await wrapper.find('[data-testid=snapshot-summary-remove-gap-rows]').trigger('click');

    expect(wrapper.emitted<[number[]]>('remove-balances')![0][0]).toEqual([1]);
  });

  it('should say what a spam removal leaves to reconcile when the typed totals are a little off', () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1000)], [location('blockchain', 90), location('total', 90)]),
      mismatch: { balancesSum: bigNumberify(1100), locationsSum: bigNumberify(90), storedTotal: bigNumberify(90) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-gap-partial]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=snapshot-summary-remove-gap-rows]').exists()).toBe(true);
  });

  it('should not offer the removal when no row explains the mismatch', () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1000)], [location('blockchain', 1050), location('total', 1100)]),
      mismatch: { balancesSum: bigNumberify(1100), locationsSum: bigNumberify(1050), storedTotal: bigNumberify(1100) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-reconcile]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=snapshot-summary-gap-rows]').exists()).toBe(false);
  });

  it('should not reconcile into a location the difference would push below zero', async () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 50)], [location('kraken', 60), location('ledger', 20), location('total', 80)]),
      mismatch: { balancesSum: bigNumberify(50), locationsSum: bigNumberify(80), storedTotal: bigNumberify(80) },
    });

    wrapper.findComponent(LocationSelector).vm.$emit('update:modelValue', 'ledger');
    await nextTick();

    expect(wrapper.find('[data-testid=snapshot-summary-reconcile-apply]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=snapshot-summary-no-reconcile-target]').exists()).toBe(false);
  });

  it('should point to the locations when no location can absorb the difference', () => {
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 10)], [location('kraken', 60), location('ledger', 40), location('total', 100)]),
      mismatch: { balancesSum: bigNumberify(10), locationsSum: bigNumberify(100), storedTotal: bigNumberify(100) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-no-reconcile-target]').exists()).toBe(true);
  });

  it('should offer to remove a spam liability instead of pointing to the locations', () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({
      snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1e30, BalanceType.LIABILITY)], [location('blockchain', 100), location('total', 100)]),
      mismatch: { balancesSum: bigNumberify(100).minus(1e30), locationsSum: bigNumberify(100), storedTotal: bigNumberify(100) },
    });

    expect(wrapper.find('[data-testid=snapshot-summary-remove-gap-rows]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=snapshot-summary-no-reconcile-target]').exists()).toBe(false);
    expect(fiatValue(wrapper, 'snapshot-summary-gap-value')).toBe(1e30);
  });

  it('should offer an action that shows the ignored rows it excludes', async () => {
    ignoredIds = ['SPAM'];
    const wrapper = mountSummary({ snapshot: snapshot([balance('ETH', 100), balance('SPAM', 1000)], [location('total', 1100)]) });

    await wrapper.find('[data-testid=snapshot-summary-show-excluded]').trigger('click');

    expect(wrapper.emitted('show-excluded')).toHaveLength(1);
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
