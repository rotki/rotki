import type { BalanceMutation } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { type Snapshot, ZeroValueFilter } from '@/modules/dashboard/snapshots';
import SnapshotBalanceEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog.vue';
import SnapshotBalancesTable from '@/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue';
import { SnapshotBalanceFilterKeys } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

let spamIds: string[] = [];
let ignoredIds: string[] = [];
vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters', () => ({
  useSnapshotAssetFilters: (): { isSpamAsset: (id: string) => boolean; isIgnoredAsset: (id: string) => boolean } => ({
    isIgnoredAsset: (id: string): boolean => ignoredIds.includes(id),
    isSpamAsset: (id: string): boolean => spamIds.includes(id),
  }),
}));

const TS = 1_600_000_000;

function balance(assetIdentifier: string, usdValue: number, category: BalanceType = BalanceType.ASSET): Snapshot['balancesSnapshot'][number] {
  return { amount: bigNumberify(1), assetIdentifier, category, timestamp: TS, usdValue: bigNumberify(usdValue) };
}

function createSnapshot(): Snapshot {
  return {
    balancesSnapshot: [
      balance('ETH', 100),
      balance('DAI', 30, BalanceType.LIABILITY),
      // An NFT whose amount isn't 1 — a genuine sanity warning that flags its row.
      { amount: bigNumberify(2), assetIdentifier: '_nft_0xabc_1', category: BalanceType.ASSET, timestamp: TS, usdValue: bigNumberify(40) },
      balance('USDC', 0),
      balance('SAITAMA', 5),
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TS, usdValue: bigNumberify(170) },
      { location: 'total', timestamp: TS, usdValue: bigNumberify(170) },
    ],
  };
}

const mutation: BalanceMutation = {
  balance: balance('BTC', 50),
  location: 'kraken',
};

describe('modules/dashboard/snapshots/components/SnapshotBalancesTable', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotBalancesTable>>;
  let pinia: ReturnType<typeof createPinia>;

  const stubs = {};

  function createWrapper(): VueWrapper<InstanceType<typeof SnapshotBalancesTable>> {
    return mount(SnapshotBalancesTable, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
        stubs,
      },
      props: { snapshot: createSnapshot(), timestamp: TS },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    spamIds = ['SAITAMA'];
    ignoredIds = [];
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should render the balance rows', () => {
    wrapper = createWrapper();
    expect(wrapper.find('[data-testid=snapshot-balances-table]').exists()).toBe(true);
    expect(wrapper.text()).toContain('100.00');
  });

  it('should map a dialog add submit to the add event', () => {
    wrapper = createWrapper();
    wrapper.findComponent(SnapshotBalanceEntryDialog).vm.$emit('submit', { index: null, mutation });
    expect(wrapper.emitted('add')).toEqual([[mutation]]);
    expect(wrapper.emitted('edit')).toBeUndefined();
  });

  it('should map a dialog edit submit to the edit event', () => {
    wrapper = createWrapper();
    wrapper.findComponent(SnapshotBalanceEntryDialog).vm.$emit('submit', { index: 3, mutation });
    expect(wrapper.emitted('edit')).toEqual([[{ index: 3, mutation }]]);
    expect(wrapper.emitted('add')).toBeUndefined();
  });

  it('should narrow the rows to what the filter bag holds', async () => {
    wrapper = createWrapper();
    await wrapper.setProps({ filters: { [SnapshotBalanceFilterKeys.SEARCH]: 'eth' } });
    expect(wrapper.text()).toContain('100.00');
    expect(wrapper.text()).not.toContain('30.00');
  });

  it('should offer every filter as a pill field', () => {
    wrapper = createWrapper();
    const fields = wrapper.findComponent(PillFilterBar).props('fields');
    expect(fields.map(field => field.key)).toStrictEqual([
      SnapshotBalanceFilterKeys.SEARCH,
      SnapshotBalanceFilterKeys.CATEGORY,
      SnapshotBalanceFilterKeys.SHOW_SPAM,
      SnapshotBalanceFilterKeys.SHOW_IGNORED,
      SnapshotBalanceFilterKeys.ZERO_VALUE,
    ]);
  });

  it('should flag a row caught by a sanity warning', () => {
    wrapper = createWrapper();
    expect(wrapper.find('[data-testid=snapshot-balances-flag]').exists()).toBe(true);
  });

  it('should suppress the hidden-count chip while isolating zero-value rows', () => {
    wrapper = mount(SnapshotBalancesTable, {
      global: { plugins: [pinia], provide: libraryDefaults, stubs },
      props: {
        filters: { [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY },
        snapshot: createSnapshot(),
        timestamp: TS,
      },
    });

    // USDC is the only zero-value row of the five; everything else is filtered out.
    expect(wrapper.findAll('tbody tr')).toHaveLength(1);
    expect(wrapper.find('[data-testid=snapshot-balances-hidden-count]').exists()).toBe(false);
  });

  it('should offer a bulk delete when zero-value rows exist and emit their indices', async () => {
    wrapper = createWrapper();
    const button = wrapper.find('[data-testid=snapshot-balances-bulk-delete]');
    expect(button.exists()).toBe(true);

    await button.trigger('click');

    // USDC (index 3) is the only zero-value row in the fixture; the page confirms.
    expect(wrapper.emitted('bulk-delete')).toEqual([[[3]]]);
  });

  it('should not offer a bulk delete when there are no zero-value rows', () => {
    wrapper = mount(SnapshotBalancesTable, {
      global: { plugins: [pinia], provide: libraryDefaults, stubs },
      props: { snapshot: { balancesSnapshot: [balance('ETH', 100)], locationDataSnapshot: [{ location: 'total', timestamp: TS, usdValue: bigNumberify(100) }] }, timestamp: TS },
    });
    expect(wrapper.find('[data-testid=snapshot-balances-bulk-delete]').exists()).toBe(false);
  });

  it('should lock every edit action and show a notice when not reconciled', () => {
    wrapper = mount(SnapshotBalancesTable, {
      global: { plugins: [pinia], provide: libraryDefaults, stubs },
      props: { snapshot: createSnapshot(), timestamp: TS, locked: true },
    });

    expect(wrapper.find('[data-testid=snapshot-balances-locked]').exists()).toBe(true);
    expect(wrapper.find<HTMLButtonElement>('[data-testid=snapshot-balances-add]').element.disabled).toBe(true);
    expect(wrapper.find<HTMLButtonElement>('[data-testid=snapshot-balances-bulk-delete]').element.disabled).toBe(true);
    expect(wrapper.find<HTMLButtonElement>('[data-testid=row-edit]').element.disabled).toBe(true);
    expect(wrapper.find<HTMLButtonElement>('[data-testid=row-delete]').element.disabled).toBe(true);
  });

  it('should not flag zero-value rows', () => {
    wrapper = mount(SnapshotBalancesTable, {
      global: { plugins: [pinia], provide: libraryDefaults, stubs },
      props: {
        // Reveal the zero-value row (hidden by default) so the flag check is meaningful.
        filters: { [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ALL },
        snapshot: { balancesSnapshot: [balance('USDC', 0)], locationDataSnapshot: [{ location: 'total', timestamp: TS, usdValue: bigNumberify(0) }] },
        timestamp: TS,
      },
    });
    expect(wrapper.find('[data-testid=snapshot-balances-flag]').exists()).toBe(false);
  });
});
