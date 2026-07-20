import { type AssetBalance, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import LiquityAssetBalanceList from './LiquityAssetBalanceList.vue';

function balance(asset: string): AssetBalance {
  return { amount: bigNumberify(1), asset, value: bigNumberify(2) };
}

function mountList(balances: AssetBalance[]): VueWrapper<InstanceType<typeof LiquityAssetBalanceList>> {
  return mount(LiquityAssetBalanceList, {
    props: { balances, emptyLabel: 'No gains', loading: false },
    shallow: true,
  });
}

describe('modules/staking/liquity/LiquityAssetBalanceList', () => {
  it('should render one balance per entry', () => {
    const wrapper = mountList([balance('ETH'), balance('LUSD')]);

    expect(wrapper.findAllComponents(BalanceDisplay)).toHaveLength(2);
  });

  it('should show the empty label when there are no balances', () => {
    const wrapper = mountList([]);

    expect(wrapper.findAllComponents(BalanceDisplay)).toHaveLength(0);
    expect(wrapper.text()).toContain('No gains');
  });

  it('should not show the empty label when balances exist', () => {
    const wrapper = mountList([balance('ETH')]);

    expect(wrapper.text()).not.toContain('No gains');
  });
});
