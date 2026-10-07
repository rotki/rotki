import type { HistoricalBucketRow } from '@/modules/statistics/historical-balances/historical-balances-view';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import HistoricalBalancesBuckets from '@/modules/statistics/historical-balances/components/HistoricalBalancesBuckets.vue';
import { PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';
import { createRuiPlugin } from '@/plugins/rui';

function bucket(asset: string, location: string, locationLabel: string | null): HistoricalBucketRow {
  return { amount: bigNumberify('1'), asset, location, locationLabel, priceStatus: PriceStatus.PRICED, protocol: null, value: bigNumberify('1') };
}

function createWrapper(buckets: HistoricalBucketRow[], showAsset = false): VueWrapper<InstanceType<typeof HistoricalBalancesBuckets>> {
  return mount(HistoricalBalancesBuckets, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        AssetDetails: true,
        CounterpartyDisplay: true,
        FiatDisplay: true,
        HistoryEventAccount: true,
        LocationDisplay: true,
        ValueDisplay: true,
      },
    },
    props: { buckets, showAsset },
  });
}

describe('historical balances buckets', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should name the chain of each bucket, so one address on two chains reads as two places', () => {
    const wrapper = createWrapper([bucket('USDC', 'ethereum', '0xA'), bucket('USDC', 'arbitrum_one', '0xA')]);

    expect(wrapper.findAllComponents(LocationDisplay).map(display => display.props('identifier'))).toEqual(['ethereum', 'arbitrum_one']);
  });

  it('should name each bucket\'s asset only for a collection', () => {
    const buckets = [bucket('USDC-mainnet', 'ethereum', '0xA'), bucket('USDC-arbitrum', 'arbitrum_one', '0xA')];

    expect(createWrapper(buckets).findAllComponents(AssetDetails)).toHaveLength(0);
    expect(createWrapper(buckets, true).findAllComponents(AssetDetails).map(details => details.props('asset'))).toEqual(['USDC-mainnet', 'USDC-arbitrum']);
  });
});
