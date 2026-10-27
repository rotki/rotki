import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { AccountKind, type BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import AccountDetailsHeader from '@/modules/accounts/details/AccountDetailsHeader.vue';

const ADDRESS = '0x314D5133BEB76f14Eb7f56e4cEEA6ae4C82e05e5';

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({ scrambleAddress: (address: string): string => `scrambled-${address}` }),
}));

const stubs = {
  AccountChains: true,
  FiatDisplay: true,
  LabeledAddressDisplay: true,
  RuiButton: { emits: ['click'], template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
  RuiIcon: true,
  TagDisplay: { props: ['tags'], template: '<div data-testid="tags">{{ tags.join(\',\') }}</div>' },
};

function createWrapper(tags?: string[]): VueWrapper {
  const group: BlockchainAccountGroupWithBalance = {
    address: ADDRESS,
    category: 'evm',
    chains: ['eth'],
    kind: AccountKind.ADDRESS,
    tags,
    type: 'group',
    value: bigNumberify(1),
  };
  return mount(AccountDetailsHeader, { global: { stubs }, props: { chainFilter: {}, group } });
}

describe('modules/accounts/details/AccountDetailsHeader', () => {
  it('should show the address as scrambling shows it, shortened, with the full one on hover', () => {
    const address = createWrapper().find('[data-testid=account-details-address]');

    expect(address.text()).not.toContain(ADDRESS);
    expect(address.text()).toBe(`scramble...${ADDRESS.slice(-8)}`);
    expect(address.attributes('title')).toBe(`scrambled-${ADDRESS}`);
  });

  it('should show the tags only when the account has some', () => {
    expect(createWrapper().find('[data-testid=tags]').exists()).toBe(false);
    expect(createWrapper(['hot', 'defi']).find('[data-testid=tags]').text()).toBe('hot,defi');
  });

  it('should ask to close from its close button', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=account-details-close]').trigger('click');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
