import type { MaybeRefOrGetter, Ref } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountDetailsChains from '@/modules/accounts/details/AccountDetailsChains.vue';

const { excluded, held, loading, unloaded } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { excluded: ref<string[]>([]), held: ref<string[]>([]), loading: ref<string[]>([]), unloaded: ref<string[]>([]) };
});

vi.mock('@/modules/balances/use-chains-with-balances', async () => {
  const { computed, toValue } = await import('vue');
  return {
    useChainsWithBalances: (_groupId: unknown, chains: MaybeRefOrGetter<string[]>): unknown =>
      computed<string[]>(() => toValue(chains).filter(chain => get(held).includes(chain))),
  };
});

/** Loading and unloaded are judged only for the chains the tab hands over, as the real helper does. */
vi.mock('@/modules/balances/use-balance-status', async () => {
  const { computed, toValue } = await import('vue');
  const among = (chains: MaybeRefOrGetter<string[]>, picked: Ref<string[]>): unknown =>
    computed<string[]>(() => toValue(chains).filter(chain => get(picked).includes(chain)));
  return {
    useChainLoadStates: (chains: MaybeRefOrGetter<string[]>): object => ({ loading: among(chains, loading), unloaded: among(chains, unloaded) }),
  };
});

vi.mock('@/modules/settings/general/disabled-chain-queries/use-disabled-chains', () => ({
  useDisabledChains: (): object => ({ isEveryAddressExcluded: (chain: string): boolean => get(excluded).includes(chain) }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => chain.toUpperCase() }),
}));

const stubs = {
  AccountDetailsChainSection: { props: ['chain', 'groupId'], template: '<div data-testid="chain-section-stub" :data-chain="chain" />' },
  RuiProgress: true,
};

function createWrapper(filtered = false): VueWrapper {
  return mount(AccountDetailsChains, {
    global: { stubs },
    props: { chains: ['eth', 'optimism', 'base'], filtered, groupId: '0x1', selected: undefined },
  });
}

function sections(wrapper: VueWrapper): string[] {
  return wrapper.findAll('[data-testid=chain-section-stub]').map(section => section.attributes('data-chain') ?? '');
}

describe('modules/accounts/details/AccountDetailsChains', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(held, ['eth', 'base']);
    set(loading, []);
    set(unloaded, []);
    set(excluded, []);
  });

  it('should give a section only to the chains holding something', () => {
    const wrapper = createWrapper();

    expect(sections(wrapper)).toStrictEqual(['eth', 'base']);
    expect(wrapper.find('[data-testid=account-details-no-chain-balances]').exists()).toBe(false);
  });

  it('should say the account holds nothing when no chain has anything and every chain loaded', () => {
    set(held, []);

    expect(createWrapper().find('[data-testid=account-details-no-chain-balances]').text()).toBe('account_balances.no_chain_balances');
  });

  it('should not call the account empty when the chains holding something are switched off', () => {
    set(held, []);

    expect(createWrapper(true).find('[data-testid=account-details-no-chain-balances]').text()).toBe('account_balances.no_shown_chain_balances');
  });

  it('should say chains are loading rather than that the account holds nothing while they are read', async () => {
    set(held, []);
    set(loading, ['optimism', 'base']);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-loading-chains]').text()).toBe('account_balances.loading_chain_balances::2');
    expect(wrapper.find('[data-testid=account-details-no-chain-balances]').exists()).toBe(false);

    set(loading, []);
    await nextTick();

    expect(wrapper.find('[data-testid=account-details-loading-chains]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-details-no-chain-balances]').exists()).toBe(true);
  });

  it('should name the chains whose balances did not load instead of calling the account empty', () => {
    set(held, []);
    set(unloaded, ['optimism', 'base']);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-unloaded-chains]').text()).toContain('account_balances.unloaded_chain_balances');
    expect(wrapper.find('[data-testid=account-details-no-chain-balances]').exists()).toBe(false);
  });

  it('should count a chain whose queries are switched off for the account as known to be empty', () => {
    set(held, []);
    set(unloaded, ['optimism']);
    set(excluded, ['optimism']);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-unloaded-chains]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-details-no-chain-balances]').exists()).toBe(true);
  });
});
