import type { ChainRefreshState } from '@/modules/accounts/use-category-chain-refresh';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountsStalenessIndicator from '@/modules/accounts/AccountsStalenessIndicator.vue';

const NOW = 1_700_000_000;

const { chains } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { chains: ref<ChainRefreshState[]>([]) };
});

vi.mock('@/modules/accounts/use-category-chain-refresh', async () => {
  const { computed } = await import('vue');
  return {
    useCategoryChainRefresh: (): object => ({
      chains,
      oldest: computed<ChainRefreshState | undefined>(() => get(chains).find(state => !state.skipped)),
      refreshable: computed<ChainRefreshState[]>(() => get(chains).filter(state => !state.skipped)),
    }),
  };
});

const stubs = {
  RuiIcon: true,
  RuiTooltip: { template: '<div><slot name="activator" /><div data-testid="tooltip"><slot /></div></div>' },
};

function chain(id: string, overrides: Partial<ChainRefreshState> = {}): ChainRefreshState {
  return { chain: id, name: `name:${id}`, skipped: false, timestamp: NOW - 120, ...overrides };
}

function createWrapper(): VueWrapper<InstanceType<typeof AccountsStalenessIndicator>> {
  return mount(AccountsStalenessIndicator, { global: { stubs }, props: { category: 'evm' } });
}

describe('modules/accounts/AccountsStalenessIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: NOW * 1000 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should render nothing when no chain can be refreshed', () => {
    set(chains, [chain('eth', { skipped: true })]);

    expect(createWrapper().find('[data-testid=accounts-staleness]').exists()).toBe(false);
  });

  it('should show the age alone for a single chain', () => {
    set(chains, [chain('btc')]);

    expect(createWrapper().find('[data-testid=accounts-staleness]').text()).toBe('2 minutes ago');
  });

  it('should show the age alone when every other chain is skipped', () => {
    set(chains, [chain('eth'), chain('gnosis', { skipped: true })]);

    expect(createWrapper().find('[data-testid=accounts-staleness]').text()).toBe('2 minutes ago');
  });

  it('should name the oldest chain when there are several', () => {
    set(chains, [chain('gnosis', { timestamp: NOW - 7200 }), chain('eth')]);

    expect(createWrapper().find('[data-testid=accounts-staleness]').text())
      .toBe('account_balances.staleness.oldest::name:gnosis, 2 hours ago');
  });

  it('should list every chain with its age, a never refreshed one and a skipped one', () => {
    set(chains, [chain('base', { timestamp: undefined }), chain('eth'), chain('gnosis', { skipped: true })]);

    const rows = createWrapper()
      .findAll('[data-testid=accounts-staleness-chain]')
      .map(row => row.findAll('span').map(cell => cell.text()));

    expect(rows).toStrictEqual([
      ['name:base', 'account_balances.staleness.never'],
      ['name:eth', '2 minutes ago'],
      ['name:gnosis', 'account_balances.staleness.skipped'],
    ]);
  });
});
