import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountHistorySummary from '@/modules/balances/account-history/components/AccountHistorySummary.vue';
import { createRuiPlugin } from '@/plugins/rui';

function createWrapper(change: number, processingRequired = false, shown: { asset?: string } = { asset: 'ETH' }): VueWrapper<InstanceType<typeof AccountHistorySummary>> {
  return mount(AccountHistorySummary, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { AssetAmountDisplay: { props: ['amount', 'asset'], template: '<span>{{ amount.toString() }}</span>' } },
    },
    props: {
      asset: shown.asset,
      processingRequired,
      summary: { change: bigNumberify(change), current: bigNumberify(5), start: bigNumberify(5 - change) },
    },
  });
}

describe('account history summary', () => {
  it('should show the balance at the end of the range and the change over it', () => {
    const wrapper = createWrapper(2);

    expect(wrapper.find('[data-testid=account-history-current]').text()).toContain('5');
    expect(wrapper.find('[data-testid=account-history-change]').text()).toContain('2');
  });

  it('should color a gain as success and a loss as error, and no change as neither', () => {
    const gain = createWrapper(2).find('[data-testid=account-history-change] span');
    const loss = createWrapper(-2).find('[data-testid=account-history-change] span');
    const flat = createWrapper(0).find('[data-testid=account-history-change] span');

    expect(gain.classes()).toContain('text-rui-success');
    expect(loss.classes()).toContain('text-rui-error');
    expect(flat.classes()).not.toContain('text-rui-success');
    expect(flat.classes()).not.toContain('text-rui-error');
  });

  it('should show the processing indicator only while events are pending', () => {
    expect(createWrapper(0).find('[data-testid=account-history-processing]').exists()).toBe(false);
    expect(createWrapper(0, true).find('[data-testid=account-history-processing]').exists()).toBe(true);
  });

  it('should keep its place with dashes while there is no balance to show', () => {
    const wrapper = createWrapper(2, false, {});

    expect(wrapper.find('[data-testid=account-history-current]').text()).toContain('-');
    expect(wrapper.find('[data-testid=account-history-change]').text()).not.toContain('2');
  });

  it('should leave the change out when told to', () => {
    const wrapper = mount(AccountHistorySummary, {
      global: { plugins: [createRuiPlugin({})], stubs: { AssetAmountDisplay: true } },
      props: { asset: 'ETH', showChange: false, summary: { change: bigNumberify(1), current: bigNumberify(1), start: bigNumberify(0) } },
    });

    expect(wrapper.find('[data-testid=account-history-change]').exists()).toBe(false);
  });
});
