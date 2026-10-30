import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { type AssetBalance, bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import AccountTopTokens from '@/modules/accounts/AccountTopTokens.vue';

const { balances } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { balances: ref<AssetBalance[]>([]) };
});

vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): object => ({ useBlockchainBalances: (): unknown => balances }),
}));

function holding(asset: string, value: number): AssetBalance {
  return { amount: bigNumberify(1), asset, value: bigNumberify(value) };
}

function render(opensDetails: boolean): VueWrapper {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(AccountTopTokens, {
    global: { plugins: [pinia], stubs: { AssetAmountDisplay: true, AssetIcon: true, RuiTooltip: { template: '<div><slot name="activator" /></div>' } } },
    props: { chains: ['eth'], opensDetails, row: createMock<BlockchainAccountBalance>({ address: '0xabc', kind: 'address', type: 'group' }) },
  });
}

describe('accountTopTokens', () => {
  it('should open the account\'s details from the count of the assets past the icons', async () => {
    set(balances, ['ETH', 'DAI', 'USDC', 'LINK', 'UNI'].map((asset, index) => holding(asset, 10 - index)));
    const wrapper = render(true);

    const count = wrapper.find('button[data-testid=top-asset-count]');
    expect(count.text()).toBe('+2');
    expect(count.attributes()).toHaveProperty('data-account-details-opener');
    await count.trigger('click');

    expect(wrapper.emitted('open-details')).toHaveLength(1);
  });

  it('should keep the count as plain text when the row has no details to open', () => {
    set(balances, ['ETH', 'DAI', 'USDC', 'LINK'].map((asset, index) => holding(asset, 10 - index)));
    const wrapper = render(false);

    const count = wrapper.find('[data-testid=top-asset-count]');
    expect(count.element.tagName).toBe('SPAN');
    expect(count.text()).toBe('+1');
  });
});
