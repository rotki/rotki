import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountDetailsChainSection from '@/modules/accounts/details/AccountDetailsChainSection.vue';

const { assets, lastRefreshTimestamp } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    assets: ref<AssetBalanceWithPrice[]>([]),
    lastRefreshTimestamp: ref<number | undefined>(),
  };
});

vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): object => ({ useBlockchainBalances: (): unknown => assets }),
}));

vi.mock('@/modules/balances/use-blockchain-balance-staleness', async () => {
  const { ref } = await import('vue');
  return {
    useBlockchainBalanceStaleness: (): object => ({ lastRefreshed: ref<string>('5 minutes ago'), lastRefreshTimestamp }),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => `name:${chain}` }),
}));

const stubs = {
  AccountDetailsAssets: { props: ['chains', 'groupId', 'limit'], template: '<div data-testid="assets-stub" :data-chains="chains.join(\',\')" :data-group="groupId" :data-limit="limit" />' },
  ChainIcon: true,
  FiatDisplay: { props: ['value'], template: '<span data-testid="value">{{ value.toString() }}</span>' },
};

function asset(value: number): AssetBalanceWithPrice {
  return createMock<AssetBalanceWithPrice>({ value: bigNumberify(value) });
}

function createWrapper(): VueWrapper {
  return mount(AccountDetailsChainSection, {
    global: { stubs },
    props: { chain: 'optimism', groupId: '0xabc', selected: undefined },
  });
}

describe('modules/accounts/details/AccountDetailsChainSection', () => {
  beforeEach(() => {
    set(assets, [asset(10), asset(5)]);
    set(lastRefreshTimestamp, 1000);
  });

  it('should head the section with the chain, its refresh age and the sum of its assets', () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('name:optimism');
    expect(wrapper.find('[data-testid=account-details-chain-age]').text()).toBe('5 minutes ago');
    expect(wrapper.find('[data-testid=value]').text()).toBe('15');
  });

  it('should say the chain was never refreshed when it has no timestamp', () => {
    set(lastRefreshTimestamp, undefined);

    expect(createWrapper().find('[data-testid=account-details-chain-age]').text()).toBe('account_balances.staleness.never');
  });

  it('should list the assets of this chain only', () => {
    const stub = createWrapper().find('[data-testid=assets-stub]');

    expect(stub.attributes('data-chains')).toBe('optimism');
    expect(stub.attributes('data-group')).toBe('0xabc');
  });

  it('should cap the chain at its ten most valuable assets, so a big chain does not bury the next', () => {
    expect(createWrapper().find('[data-testid=assets-stub]').attributes('data-limit')).toBe('10');
  });
});
