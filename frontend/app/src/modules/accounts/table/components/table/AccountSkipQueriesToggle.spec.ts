import type { MaybeRefOrGetter } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountSkipQueriesToggle from '@/modules/accounts/table/components/table/AccountSkipQueriesToggle.vue';
import { type SkipChainItem, SkipState } from '@/modules/accounts/table/use-account-skip-queries';

const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

const toggleAll = vi.fn<() => Promise<void>>(async () => {});
const toggleChain = vi.fn<(chain: string) => Promise<void>>(async () => {});
const scope = vi.fn<(address: string, chains: string[]) => void>();

const items = ref<SkipChainItem[]>([]);
const state = ref<SkipState>(SkipState.NONE);
const locked = ref<boolean>(false);

/**
 * Only the composable is replaced; `SkipState` comes from the real module, so the states this spec
 * drives stay the ones the component compares against.
 */
vi.mock('@/modules/accounts/table/use-account-skip-queries', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/accounts/table/use-account-skip-queries')>(),
  useAccountSkipQueries: (address: MaybeRefOrGetter<string>, chains: MaybeRefOrGetter<string[]>): {
    items: typeof items;
    locked: typeof locked;
    pending: Ref<boolean>;
    state: typeof state;
    toggleAll: typeof toggleAll;
    toggleChain: typeof toggleChain;
  } => {
    scope(toValue(address), toValue(chains));
    return { items, locked, pending: ref(false), state, toggleAll, toggleChain };
  },
}));

function chain(name: string, overrides: Partial<SkipChainItem> = {}): SkipChainItem {
  return { chain: name, name: name.toUpperCase(), skipped: false, wholeChain: false, ...overrides };
}

describe('modules/accounts/table/components/table/AccountSkipQueriesToggle', () => {
  let wrapper: VueWrapper;

  function createWrapper(props: { address: string; chains: string[]; disabled?: boolean }): VueWrapper {
    return mount(AccountSkipQueriesToggle, {
      global: {
        stubs: {
          ChainIcon: true,
          RuiMenu: { props: ['disabled'], template: '<div><slot name="activator" v-bind="{ attrs: {} }" /><slot v-if="!disabled" /></div>' },
          RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
        },
      },
      props,
    });
  }

  function button(): ReturnType<VueWrapper['find']> {
    return wrapper.find('[data-testid=account-skip-queries]');
  }

  function chainItems(): ReturnType<VueWrapper['findAll']> {
    return wrapper.findAll('[data-testid=account-skip-queries-chain]');
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(items, [chain('eth')]);
    set(state, SkipState.NONE);
    set(locked, false);
  });

  it('should ask about the account and chains it was given', () => {
    wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism'] });

    expect(scope).toHaveBeenCalledWith(ADDRESS, ['eth', 'optimism']);
  });

  describe('a row standing for one chain', () => {
    it('should toggle it directly, with no menu to open', async () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth'] });

      expect(chainItems()).toHaveLength(0);
      await button().trigger('click');

      expect(toggleAll).toHaveBeenCalledTimes(1);
    });

    it('should name the chain in the tooltip', () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth'] });

      expect(wrapper.text()).toContain('account_balances.skip_queries.skip::ETH');
    });

    it('should offer to query it again once it is skipped', () => {
      set(items, [chain('eth', { skipped: true })]);
      set(state, SkipState.ALL);

      wrapper = createWrapper({ address: ADDRESS, chains: ['eth'] });

      expect(wrapper.text()).toContain('account_balances.skip_queries.resume::ETH');
    });
  });

  describe('a row standing for several chains', () => {
    beforeEach(() => {
      set(items, [chain('eth', { skipped: true }), chain('optimism'), chain('base', { wholeChain: true })]);
      set(state, SkipState.PARTIAL);
    });

    it('should offer one entry per chain, and act on that chain alone', async () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      expect(chainItems()).toHaveLength(3);
      await wrapper.find('[data-testid=account-skip-queries-chain][data-chain=optimism]').trigger('click');

      expect(toggleChain).toHaveBeenCalledWith('optimism');
      expect(toggleAll).not.toHaveBeenCalled();
    });

    it('should not act on a chain that is switched off whole', () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      const wholeChain = wrapper.find('[data-testid=account-skip-queries-chain][data-chain=base]');
      expect(wholeChain.attributes('disabled')).toBeDefined();
      expect(wholeChain.text()).toContain('account_balances.skip_queries.chain_whole');
    });

    it('should say which chains are already skipped', () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      expect(wrapper.find('[data-testid=account-skip-queries-chain][data-chain=eth]').text())
        .toContain('account_balances.skip_queries.chain_skipped');
      expect(wrapper.find('[data-testid=account-skip-queries-chain][data-chain=optimism]').text())
        .not
        .toContain('account_balances.skip_queries.chain_skipped');
    });

    it('should offer to skip them all while some are still queried, counting only the chains it can act on', async () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      const all = wrapper.find('[data-testid=account-skip-queries-all]');
      expect(all.text()).toContain('account_balances.skip_queries.skip_all::2');
      await all.trigger('click');

      expect(toggleAll).toHaveBeenCalledTimes(1);
    });

    it('should offer to query them all again once every chain is skipped', () => {
      set(state, SkipState.ALL);

      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      expect(wrapper.find('[data-testid=account-skip-queries-all]').text())
        .toContain('account_balances.skip_queries.resume_all::2');
    });

    it('should not toggle anything when the button only opens the menu', async () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['eth', 'optimism', 'base'] });

      await button().trigger('click');

      expect(toggleAll).not.toHaveBeenCalled();
      expect(toggleChain).not.toHaveBeenCalled();
    });
  });

  describe('state colour', () => {
    it.each<[SkipState, boolean, boolean]>([
      [SkipState.NONE, false, false],
      [SkipState.PARTIAL, false, true],
      [SkipState.ALL, true, false],
    ])('should draw %s with error=%s and warning=%s', (value, error, warning) => {
      set(state, value);

      wrapper = createWrapper({ address: ADDRESS, chains: ['eth'] });

      const classes = button().classes();
      expect(classes.includes('text-rui-error')).toBe(error);
      expect(classes.includes('text-rui-warning')).toBe(warning);
    });
  });

  describe('when every chain is switched off whole', () => {
    beforeEach(() => {
      set(locked, true);
    });

    it('should stay hoverable so the tooltip can explain why, rather than go natively disabled', async () => {
      wrapper = createWrapper({ address: ADDRESS, chains: ['base'] });

      expect(button().attributes('disabled')).toBeUndefined();
      expect(button().attributes('aria-disabled')).toBe('true');
      expect(wrapper.text()).toContain('account_balances.skip_queries.entire_chain');

      await button().trigger('click');

      expect(toggleAll).not.toHaveBeenCalled();
    });

    it('should offer no menu to open', () => {
      set(items, [chain('base', { wholeChain: true }), chain('gnosis', { wholeChain: true })]);

      wrapper = createWrapper({ address: ADDRESS, chains: ['base', 'gnosis'] });

      expect(chainItems()).toHaveLength(0);
    });
  });

  it('should disable itself while an account operation is running', () => {
    wrapper = createWrapper({ address: ADDRESS, chains: ['eth'], disabled: true });

    expect(button().attributes('disabled')).toBeDefined();
  });
});
