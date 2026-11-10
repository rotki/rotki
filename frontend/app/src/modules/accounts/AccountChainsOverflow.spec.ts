import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import AccountChainsOverflow, { type AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';

const { toggleChain } = vi.hoisted(() => ({
  toggleChain: vi.fn<(chain: string) => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/accounts/table/use-account-skip-queries', () => ({
  useAccountSkipQueries: (): Record<string, unknown> => ({
    items: computed(() => [{ chain: 'gnosis', name: 'Gnosis', skipped: true, wholeChain: true }]),
    labelFor: (chain: string): string => `label of ${chain}`,
    pending: ref<boolean>(false),
    toggleChain,
  }),
}));

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
  function createWrapper(items: AccountChainState[] = ITEMS, skipAddress?: string): VueWrapper {
    return mount(AccountChainsOverflow, {
      attachTo: document.body,
      global: {
        stubs: {
          AccountChainSkipButton: {
            emits: ['toggle'],
            props: ['chain', 'label', 'locked', 'skipped', 'pending'],
            template: '<button data-testid="skip-button-stub" :data-chain="chain" :data-label="label" :data-locked="locked" :data-skipped="skipped" @click="$emit(\'toggle\')" />',
          },
          ChainIcon,
        },
      },
      props: { items, skipAddress },
    });
  }

  function menuItem(chain: string): HTMLElement | null {
    return document.body.querySelector<HTMLElement>(`[data-testid="account-chains-more-item"][data-chain="${chain}"]`);
  }

  async function opened(skipAddress?: string): Promise<VueWrapper> {
    const wrapper = createWrapper(ITEMS, skipAddress);
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

  function skipButtons(): (string | null)[] {
    return Array.from(
      document.body.querySelectorAll('[data-testid="skip-button-stub"]'),
      button => button.getAttribute('data-chain'),
    );
  }

  it('should offer a skip beside each chain on a row that can carry one', async () => {
    await opened('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');

    expect(skipButtons()).toStrictEqual(['optimism', 'base', 'gnosis']);
  });

  it('should offer no skip on a row that cannot', async () => {
    await opened();

    expect(skipButtons()).toStrictEqual([]);
  });

  it('should report when its menu opens, so the row can hold its order', async () => {
    const wrapper = await opened();

    expect(wrapper.emitted('update:open')?.at(-1)).toStrictEqual([true]);
  });

  it('should hand each skip button its own wording and state', async () => {
    await opened('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');

    const gnosis = document.body.querySelector('[data-testid="skip-button-stub"][data-chain="gnosis"]');
    expect(gnosis?.getAttribute('data-label')).toBe('label of gnosis');
    expect(gnosis?.getAttribute('data-skipped')).toBe('true');
    expect(gnosis?.getAttribute('data-locked')).toBe('true');
  });

  it('should skip the chain its button belongs to', async () => {
    await opened('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');

    document.body.querySelector<HTMLElement>('[data-testid="skip-button-stub"][data-chain="base"]')?.click();

    expect(toggleChain).toHaveBeenCalledExactlyOnceWith('base');
  });

  it('should report its menu closed when it goes away while open', async () => {
    const wrapper = await opened();

    wrapper.unmount();

    expect(wrapper.emitted('update:open')?.at(-1)).toStrictEqual([false]);
  });
});
