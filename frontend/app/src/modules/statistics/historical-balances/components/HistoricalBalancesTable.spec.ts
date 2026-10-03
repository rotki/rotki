import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import HistoricalBalancesBuckets from '@/modules/statistics/historical-balances/components/HistoricalBalancesBuckets.vue';
import HistoricalBalancesTable from '@/modules/statistics/historical-balances/components/HistoricalBalancesTable.vue';
import { type HistoricalAssetRow, PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';
import { createRuiPlugin } from '@/plugins/rui';

function row(asset: string, amount: string, value?: string, unpriced: PriceStatus = PriceStatus.PENDING): HistoricalAssetRow {
  return {
    amount: bigNumberify(amount),
    asset,
    buckets: [{ amount: bigNumberify(amount), location: 'ethereum', locationLabel: '0xA', protocol: null }],
    price: value ? bigNumberify(value).div(amount) : undefined,
    priceStatus: value ? PriceStatus.PRICED : unpriced,
    value: value ? bigNumberify(value) : undefined,
  };
}

function createWrapper(rows: HistoricalAssetRow[]): VueWrapper<InstanceType<typeof HistoricalBalancesTable>> {
  return mount(HistoricalBalancesTable, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        AssetDetails: true,
        FiatDisplay: true,
        HistoricalBalancesBuckets: true,
        ValueDisplay: true,
      },
    },
    props: { rows },
  });
}

function assetOrder(wrapper: VueWrapper): string[] {
  return wrapper.findAllComponents(AssetDetails).map(details => String(details.props('asset')));
}

describe('historical balances table', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should order assets by value, with still-unpriced ones last by amount', () => {
    const wrapper = createWrapper([
      row('DAI', '10', '10'),
      row('PEPE', '5'),
      row('ETH', '1', '2000'),
      row('SHIB', '900'),
    ]);

    expect(assetOrder(wrapper)).toEqual(['ETH', 'DAI', 'SHIB', 'PEPE']);
  });

  it('should put spam below everything, however large its amount', () => {
    const wrapper = createWrapper([
      row('MONONOKE', '1800000000000000', undefined, PriceStatus.SPAM),
      row('RARE', '5', undefined, PriceStatus.MISSING),
      row('DAI', '10', '10'),
    ]);

    expect(assetOrder(wrapper)).toEqual(['DAI', 'RARE', 'MONONOKE']);
  });

  it('should show an asset\'s buckets at its price when it is expanded', async () => {
    const wrapper = createWrapper([row('ETH', '1', '2000')]);

    expect(wrapper.findComponent(HistoricalBalancesBuckets).exists()).toBe(false);

    await wrapper.find('tbody button').trigger('click');

    const buckets = wrapper.findComponent(HistoricalBalancesBuckets);
    expect(buckets.exists()).toBe(true);
    expect(buckets.props('buckets')).toHaveLength(1);
    expect(buckets.props('price')?.toString()).toBe('2000');
  });
});
