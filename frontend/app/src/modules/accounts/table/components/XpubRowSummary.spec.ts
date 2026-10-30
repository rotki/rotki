import type { XpubGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import { Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import XpubRowSummary from '@/modules/accounts/table/components/XpubRowSummary.vue';

function xpubGroup(extras: Partial<XpubGroupWithBalance> = {}): XpubGroupWithBalance {
  return {
    addressCount: 0,
    amount: Zero,
    category: 'bitcoin',
    chains: ['btc'],
    fundedAddressCount: 0,
    kind: 'xpub',
    nativeAsset: 'BTC',
    type: 'group',
    value: Zero,
    xpub: 'xpub1',
    ...extras,
  };
}

function render(group: XpubGroupWithBalance): VueWrapper {
  return mount(XpubRowSummary, {
    global: { stubs: { RuiChip: { template: '<span><slot /></span>' } } },
    props: { group },
  });
}

describe('xpubRowSummary', () => {
  it('should name the address type and count the addresses holding a balance', () => {
    const wrapper = render(xpubGroup({ addressCount: 6, addressType: 'native_segwit', fundedAddressCount: 4 }));

    expect(wrapper.find('[data-testid=xpub-address-type]').text()).toBe('account_form.xpub_detected.native_segwit');
    expect(wrapper.find('[data-testid=xpub-funded-count]').text()).toBe('account_balances.xpub.funded::6, 4');
  });

  it('should leave the type out while it is undecided and still count the addresses', () => {
    const wrapper = render(xpubGroup({ addressCount: 3 }));

    expect(wrapper.find('[data-testid=xpub-address-type]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=xpub-funded-count]').exists()).toBe(true);
  });

  it('should render nothing for an xpub with no type and no derived address', () => {
    const wrapper = render(xpubGroup());

    expect(wrapper.find('[data-testid=xpub-row-summary]').exists()).toBe(false);
  });
});
