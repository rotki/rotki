import type { SnapshotChange } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import SnapshotChangesList from '@/modules/dashboard/snapshots/components/SnapshotChangesList.vue';

const TIMESTAMP = 1_600_000_000;

function mountList(changes: SnapshotChange[]): VueWrapper {
  return mount(SnapshotChangesList, {
    global: {
      provide: libraryDefaults,
      stubs: {
        AssetDetails: true,
        LocationDisplay: true,
        SnapshotFiatDisplay: true,
      },
    },
    props: { changes, timestamp: TIMESTAMP },
  });
}

describe('snapshotChangesList', () => {
  it('should render the empty state with no changes', () => {
    const wrapper = mountList([]);
    expect(wrapper.find('[data-testid=snapshot-changes-empty]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=snapshot-changes-list]').exists()).toBe(false);
  });

  it('should render one row per change', () => {
    const wrapper = mountList([
      { after: { amount: bigNumberify(1), assetIdentifier: 'ETH', category: BalanceType.ASSET, timestamp: TIMESTAMP, usdValue: bigNumberify(100) }, index: 0, kind: 'balance-added' },
      { after: bigNumberify(120), before: bigNumberify(100), kind: 'location-changed', location: 'kraken' },
      { after: bigNumberify(120), before: bigNumberify(100), kind: 'total-changed' },
    ]);
    expect(wrapper.find('[data-testid=snapshot-changes-list]').exists()).toBe(true);
    expect(wrapper.findAll('li')).toHaveLength(3);
  });
});
