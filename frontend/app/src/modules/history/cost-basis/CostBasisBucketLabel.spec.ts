import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import CostBasisBucketLabel from '@/modules/history/cost-basis/CostBasisBucketLabel.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getChainName: (location: string) => string; matchChain: (location: string) => string | undefined } => ({
    getChainName: (location: string): string => location,
    matchChain: (location: string): string | undefined => (location === 'ethereum' ? 'eth' : undefined),
  }),
}));

const stubs = {
  LocationIcon: true,
  RuiTooltip: { template: '<div><slot name="activator" /><div class="tooltip"><slot /></div></div>' },
};

function mountLabel(props: { location: string; locationLabel?: string | null; method?: string; protocol?: string | null }): VueWrapper {
  return mount(CostBasisBucketLabel, {
    global: { stubs },
    props: { locationLabel: null, method: 'fifo', protocol: null, ...props },
  });
}

function holder(wrapper: VueWrapper): string | undefined {
  const element = wrapper.find('[data-testid=cost-basis-bucket-holder]');
  return element.exists() ? element.text() : undefined;
}

describe('costBasisBucketLabel.vue', () => {
  it('should name the wallet on a chain and nothing on an exchange', () => {
    expect(holder(mountLabel({ location: 'ethereum' }))).toBe('accounting_overlay.wallet');
    expect(holder(mountLabel({ location: 'kraken' }))).toBeUndefined();
  });

  it('should name the protocol when there is one, and join the account label to it', () => {
    expect(holder(mountLabel({ location: 'ethereum', locationLabel: '0xA', protocol: 'aave' }))).toBe('aave · 0xA');
    expect(holder(mountLabel({ location: 'kraken', locationLabel: 'main' }))).toBe('main');
  });

  it('should show the method and its full name', () => {
    const wrapper = mountLabel({ location: 'ethereum', method: 'hifo' });
    expect(wrapper.get('[data-testid=cost-basis-method]').text()).toBe('hifo');
    expect(wrapper.get('.tooltip').text()).toBe('account_settings.cost_basis_method_settings.labels.hifo');
  });
});
