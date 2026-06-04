import type { AccountingOverlayBucket } from './use-accounting-overlay';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountingOverlayBuckets from './AccountingOverlayBuckets.vue';

const stubs = {
  AccountingOverlayBucketIcon: { template: '<i class="bucket-icon" />' },
  AssetAmountDisplay: { props: ['amount', 'asset', 'decimals'], template: '<span class="amount" :data-decimals="decimals">{{ amount?.toString() }}</span>' },
  AssetValueDisplay: { props: ['amount', 'asset', 'timestamp'], template: '<span class="value" />' },
  DateDisplay: { props: ['timestamp'], template: '<span class="date" />' },
  EnsAvatar: { props: ['address'], template: '<i class="ens-avatar" :data-address="address" />' },
  LocationIcon: { props: ['item'], template: '<i class="location-icon" :data-location="item" />' },
  RuiDivider: { template: '<hr>' },
  RuiIcon: { props: ['name'], template: '<i class="icon" :data-name="name" />' },
  RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
};

function bucket(protocol: string | null, balance: string): AccountingOverlayBucket {
  return { balance: bigNumberify(balance), location: 'ethereum', protocol };
}

function mountBuckets(buckets: AccountingOverlayBucket[], timestamp?: number, account?: string): VueWrapper {
  return mount(AccountingOverlayBuckets, { global: { stubs }, props: { account, asset: 'ETH', buckets, timestamp } });
}

describe('accountingOverlayBuckets.vue', () => {
  it('should render a single bucket with no total row', () => {
    const wrapper = mountBuckets([bucket(null, '5')]);
    expect(wrapper.findAll('.amount')).toHaveLength(1);
  });

  it('should render a total row that sums the buckets', () => {
    const wrapper = mountBuckets([bucket(null, '5'), bucket('aave-v3', '2')]);
    const amounts = wrapper.findAll('.amount');
    expect(amounts).toHaveLength(3); // two buckets + total
    expect(amounts.at(-1)?.text()).toBe('7');
  });

  it('should align every amount to the widest decimal precision', () => {
    const wrapper = mountBuckets([bucket(null, '5.12'), bucket('aave-v3', '2.3456')]);
    wrapper.findAll('.amount').forEach(amount => expect(amount.attributes('data-decimals')).toBe('4'));
  });

  it('should cap displayed decimals and warn when precision is excessive', () => {
    const huge = `0.${'1'.repeat(30)}`; // 30 decimal places, above the 24 cap
    const wrapper = mountBuckets([bucket(null, huge)]);
    wrapper.findAll('.amount').forEach(amount => expect(amount.attributes('data-decimals')).toBe('24'));
    expect(wrapper.find('[data-name="lu-triangle-alert"]').exists()).toBe(true);
  });

  it('should not warn when precision is within the cap', () => {
    const wrapper = mountBuckets([bucket(null, '5.12')]);
    expect(wrapper.find('[data-name="lu-triangle-alert"]').exists()).toBe(false);
  });

  it('should render fiat values only when a timestamp is provided', () => {
    expect(mountBuckets([bucket(null, '5')]).findAll('.value')).toHaveLength(0);
    expect(mountBuckets([bucket(null, '5')], 150_000).findAll('.value')).toHaveLength(1);
  });

  it('should show the account blockie and shortened address for a protocol-less bucket', () => {
    const account = '0x1234567890abcdef';
    const wrapper = mountBuckets([bucket(null, '5')], undefined, account);
    const avatar = wrapper.find('.ens-avatar');
    expect(avatar.exists()).toBe(true);
    expect(avatar.attributes('data-address')).toBe(account);
    expect(wrapper.text()).toContain('0x123456');
    expect(wrapper.find('[title]').attributes('title')).toBe(account);
  });

  it('should render a location icon per bucket to disambiguate same-address rows', () => {
    const wrapper = mountBuckets([bucket(null, '5'), bucket(null, '2')], undefined, '0x1234567890abcdef');
    const icons = wrapper.findAll('.location-icon');
    expect(icons).toHaveLength(2);
    expect(icons.at(0)?.attributes('data-location')).toBe('ethereum');
  });

  it('should highlight only the bucket the triggering event moved', () => {
    const buckets = [bucket(null, '5'), bucket('aave-v3', '2')];
    const wrapper = mount(AccountingOverlayBuckets, {
      global: { stubs },
      props: { asset: 'ETH', buckets, eventLocation: 'ethereum', eventProtocol: 'aave-v3' },
    });
    const highlighted = wrapper.findAll('.ring-rui-primary\\/20');
    expect(highlighted).toHaveLength(1);
    expect(highlighted.at(0)?.text()).toContain('aave-v3');
  });

  it('should highlight the only bucket even when the protocol does not match', () => {
    // A deposit-into-protocol event carries the protocol counterparty, but the moved asset may live
    // in the plain wallet (one bucket); the single position is unambiguously the affected one.
    const wrapper = mount(AccountingOverlayBuckets, {
      global: { stubs },
      props: { asset: 'ETH', buckets: [bucket(null, '5')], eventLocation: 'ethereum', eventProtocol: 'aave-v3' },
    });
    expect(wrapper.findAll('.ring-rui-primary\\/20')).toHaveLength(1);
  });

  it('should fall back to the wallet label when no account is provided', () => {
    const wrapper = mountBuckets([bucket(null, '5')]);
    expect(wrapper.find('.ens-avatar').exists()).toBe(false);
    expect(wrapper.find('.icon').exists()).toBe(true);
  });
});
