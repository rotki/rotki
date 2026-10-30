import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import AccountChainsOverflow, { type AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getChainName: (chain: string) => string } => ({
    getChainName: (chain: string): string => `name of ${chain}`,
  }),
}));

const ChainIcon = {
  name: 'ChainIcon',
  props: ['chain', 'size'],
  template: '<span data-testid="chain-icon" />',
};

const ITEMS: AccountChainState[] = [
  { chain: 'optimism', detected: true, enabled: true, skipped: false },
  { chain: 'base', detected: true, enabled: false, skipped: false },
  { chain: 'gnosis', detected: true, enabled: true, skipped: true },
];

describe('accountChainsOverflow', () => {
  function createWrapper(items: AccountChainState[] = ITEMS): VueWrapper {
    return mount(AccountChainsOverflow, {
      attachTo: document.body,
      global: { stubs: { ChainIcon } },
      props: { items },
    });
  }

  function menuItem(chain: string): HTMLElement | null {
    return document.body.querySelector<HTMLElement>(`[data-testid="account-chains-more-item"][data-chain="${chain}"]`);
  }

  async function opened(): Promise<VueWrapper> {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid="account-chains-more"]').trigger('click');
    await vi.waitFor(() => expect(menuItem('optimism')).not.toBeNull());
    return wrapper;
  }

  it('should count the hidden chains on the button and name them in its label', () => {
    const button = createWrapper().find('[data-testid="account-chains-more"]');

    expect(button.text()).toBe('+3');
    expect(button.attributes('aria-label')).toBe(mockT('account_balances.chain_filter.more', { count: 3 }));
  });

  it('should list every hidden chain by name once the button is clicked', async () => {
    await opened();

    expect(ITEMS.map(({ chain }) => menuItem(chain)?.textContent)).toStrictEqual([
      expect.stringContaining('name of optimism'),
      expect.stringContaining('name of base'),
      expect.stringContaining('name of gnosis'),
    ]);
  });

  it('should mark a filtered out chain as excluded and a skipped one as skipped', async () => {
    await opened();

    expect(menuItem('optimism')?.textContent).not.toContain('account_balances');
    expect(menuItem('base')?.textContent).toContain('account_balances.chain_filter.excluded');
    expect(menuItem('gnosis')?.textContent).toContain('account_balances.skip_queries.chain_skipped');
  });

  it('should ask to flip a chain\'s filter when its entry is clicked', async () => {
    const wrapper = await opened();

    menuItem('optimism')?.click();
    menuItem('base')?.click();

    expect(wrapper.emitted('toggle')).toStrictEqual([
      [{ chain: 'optimism', enabled: false }],
      [{ chain: 'base', enabled: true }],
    ]);
  });
});
