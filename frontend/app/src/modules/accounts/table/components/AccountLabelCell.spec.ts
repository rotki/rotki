import { Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { AccountKind, type BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import AccountLabelCell from '@/modules/accounts/table/components/AccountLabelCell.vue';

function render(row: BlockchainAccountBalance): VueWrapper {
  return mount(AccountLabelCell, {
    global: { stubs: { LabeledAddressDisplay: true, XpubRowSummary: { props: ['group'], template: '<div data-testid="xpub-summary-stub" />' } } },
    props: { row },
  });
}

describe('accountLabelCell', () => {
  it('should add the xpub summary under an xpub row', () => {
    const wrapper = render({
      addressCount: 2,
      amount: Zero,
      category: 'bitcoin',
      chains: ['btc'],
      fundedAddressCount: 1,
      kind: AccountKind.XPUB,
      nativeAsset: 'BTC',
      type: 'group',
      value: Zero,
      xpub: 'xpub1',
    });

    expect(wrapper.find('[data-testid=xpub-summary-stub]').exists()).toBe(true);
  });

  it('should show only the label for an address row', () => {
    const wrapper = render({ address: 'bc1-plain', category: 'bitcoin', chains: ['btc'], kind: AccountKind.ADDRESS, type: 'group', value: Zero });

    expect(wrapper.find('[data-testid=xpub-summary-stub]').exists()).toBe(false);
  });
});
