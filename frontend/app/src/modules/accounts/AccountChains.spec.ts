import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountChains from '@/modules/accounts/AccountChains.vue';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const { menuClick } = vi.hoisted(() => ({
  menuClick: vi.fn<() => void>(),
}));

/** Renders the menu's content always, and hands out activator handlers the spec can watch. */
const RuiMenuStub = {
  name: 'RuiMenu',
  emits: ['update:modelValue'],
  props: ['modelValue'],
  setup(): { handlers: { onClick: () => void } } {
    return { handlers: { onClick: menuClick } };
  },
  template: '<div><slot name="activator" :attrs="handlers" /><slot /></div>',
};

describe('modules/accounts/AccountChains', () => {
  const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

  let wrapper: VueWrapper;

  function setDisabled(value: Record<string, string[]>): void {
    const store = useSettingsRepo();
    store.updateGeneral({ ...store.general, disabledChainQueries: value });
  }

  function createWrapper(props: { address?: string; row: { chains: string[]; id: string }; skippable?: boolean }): VueWrapper {
    return mount(AccountChains, {
      global: {
        stubs: {
          AccountChainsOverflow: { name: 'AccountChainsOverflow', emits: ['update:open'], props: ['items'], template: '<div data-testid="overflow-stub" :data-skipped="items.filter(item => item.skipped).map(item => item.chain).join()">{{ items.map(item => item.chain).join() }}</div>' },
          AccountSkipQueriesToggle: { props: ['address', 'chains'], template: '<div data-testid="skip-toggle" :data-address="address" :data-chains="chains.join()" />' },
          ChainIcon: true,
          I18nT: { props: ['keypath'], template: '<span>{{ keypath }}</span>' },
          RuiMenu: RuiMenuStub,
          RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
        },
      },
      props: { chainFilter: {}, ...props },
    });
  }

  /** The skipped chains, whether marked on an icon or listed behind the "+N". */
  function markedChains(): string[] {
    const onIcons = Array.from(wrapper.findAll('[data-testid=account-chain-skipped]'), el => el.attributes('data-chain') ?? '');
    const overflow = wrapper.find('[data-testid=overflow-stub]');
    const behindMore = overflow.exists() ? (overflow.attributes('data-skipped') ?? '').split(',').filter(Boolean) : [];
    return [...onIcons, ...behindMore];
  }

  /** Rests the pointer on a chain's icon, which is what the row's menu describes. */
  async function pointAt(chain: string): Promise<void> {
    await wrapper.find(`[data-chain=${chain}][data-testid=account-chain]`).trigger('mouseenter');
  }

  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  it('should mark only the chains the address is excluded on', () => {
    setDisabled({ optimism: [ADDRESS] });

    wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

    expect(markedChains()).toEqual(['optimism']);
  });

  it('should mark a chain that is switched off whole, which has no rule of its own', () => {
    setDisabled({ eth: [] });

    wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

    expect(markedChains()).toEqual(['eth']);
  });

  it('should mark nothing when the row carries no address, as an xpub group does not', () => {
    setDisabled({ eth: [], optimism: [ADDRESS] });

    wrapper = createWrapper({ row: { chains: ['eth', 'optimism'], id: 'xpub1' } });

    expect(markedChains()).toEqual([]);
  });

  it('should say why the chain is marked, in place of the bare chain name', async () => {
    setDisabled({ eth: [ADDRESS] });

    wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth'], id: ADDRESS } });
    await pointAt('eth');

    expect(wrapper.find('[data-testid=account-chain-skipped-tooltip]').text())
      .toContain('account_balances.skip_queries.chain_marker');
    const tooltip = wrapper.find('[data-testid=account-chain-skipped-tooltip]').element.parentElement;
    expect(tooltip?.textContent?.replace('lu-ban', '').trim()).toBe('account_balances.skip_queries.chain_marker::Eth');
  });

  describe('the detection marker', () => {
    function detectedChains(): string[] {
      return Array.from(wrapper.findAll('[data-testid=account-chain][data-detected]'), el => el.attributes('data-chain') ?? '');
    }

    function chip(): string | undefined {
      const element = wrapper.find('[data-testid=account-chains-detected-tooltip]');
      return element.exists() ? element.text() : undefined;
    }

    it('should ring only the chains detection added the address on', () => {
      useDetectedAccountsStore().record([{ address: ADDRESS, chain: 'optimism' }, { address: '0xother', chain: 'eth' }]);

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

      expect(detectedChains()).toEqual(['optimism']);
    });

    it('should mark nothing on a row without an address', () => {
      useDetectedAccountsStore().record([{ address: 'xpub1', chain: 'eth' }]);

      wrapper = createWrapper({ row: { chains: ['eth'], id: 'xpub1' } });

      expect(detectedChains()).toEqual([]);
      expect(chip()).toBeUndefined();
    });

    it('should name the detected chains once, on the row chip', () => {
      useDetectedAccountsStore().record([{ address: ADDRESS, chain: 'eth' }]);

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

      expect(chip()).toBe('account_balances.detected.tooltip::Eth');
    });

    it('should name the chains in the order the row draws them, not the order detection found them', () => {
      useDetectedAccountsStore().record([{ address: ADDRESS, chain: 'optimism' }, { address: ADDRESS, chain: 'eth' }]);

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'base', 'optimism'], id: ADDRESS } });

      expect(chip()).toBe('account_balances.detected.tooltip::Eth, Optimism');
    });

    it('should drop the rings and the chip when the chip is clicked', async () => {
      useDetectedAccountsStore().record([{ address: ADDRESS, chain: 'eth' }]);
      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

      await wrapper.find('[data-testid=account-chains-detected]').trigger('click');

      expect(detectedChains()).toEqual([]);
      expect(chip()).toBeUndefined();
    });

    it('should show no chip on a row detection did not touch', () => {
      useDetectedAccountsStore().record([{ address: '0xother', chain: 'eth' }]);

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth'], id: ADDRESS } });

      expect(chip()).toBeUndefined();
    });

    it('should leave the chain tooltip naming the chain, with the detection on the chip only', async () => {
      useDetectedAccountsStore().record([{ address: ADDRESS, chain: 'eth' }]);

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth'], id: ADDRESS } });
      await pointAt('eth');

      expect(wrapper.find('[data-testid=account-chain-menu]').text()).toBe('Eth');
    });
  });

  describe('the hover menu', () => {
    const skippableRow = { address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS }, skippable: true };

    function toggles(): { address?: string; chains?: string }[] {
      return wrapper.findAll('[data-testid=skip-toggle]').map(el => ({
        address: el.attributes('data-address'),
        chains: el.attributes('data-chains'),
      }));
    }

    it('should describe the chain under the pointer, and offer to skip only that one', async () => {
      wrapper = createWrapper(skippableRow);

      await pointAt('eth');
      expect(toggles()).toEqual([{ address: ADDRESS, chains: 'eth' }]);

      await pointAt('optimism');
      expect(toggles()).toEqual([{ address: ADDRESS, chains: 'optimism' }]);
    });

    it('should offer no skip on a row the backend cannot match a rule against', async () => {
      wrapper = createWrapper({ address: 'xpub1', row: { chains: ['eth', 'optimism'], id: 'xpub1' } });

      await pointAt('eth');

      expect(wrapper.find('[data-testid=account-chain-menu]').exists()).toBe(true);
      expect(toggles()).toEqual([]);
    });

    it('should offer the skip on a single-chain row, which has nothing to hide', async () => {
      wrapper = createWrapper({ ...skippableRow, row: { chains: ['eth'], id: ADDRESS } });

      await pointAt('eth');

      expect(toggles()).toEqual([{ address: ADDRESS, chains: 'eth' }]);
      expect(wrapper.find('[data-testid=account-chain-menu]').text()).toBe('Eth');
    });

    it('should explain the click on a row it filters', async () => {
      wrapper = createWrapper(skippableRow);

      await pointAt('eth');

      expect(wrapper.find('[data-testid=account-chain-menu]').text()).toContain('account_balances.chain_filter.remove');
    });

    it('should leave the click to the filter rather than to the menu', async () => {
      wrapper = createWrapper(skippableRow);

      await wrapper.find('[data-chain=eth][data-testid=account-chain]').trigger('click');

      expect(menuClick).not.toHaveBeenCalled();
      expect(wrapper.emitted('update:chainFilter')).toHaveLength(1);
    });
  });

  describe('the skipped chains', () => {
    const CHAINS = ['eth', 'optimism', 'base', 'gnosis', 'polygon_pos', 'arbitrum_one', 'scroll'];

    /** In reading order: the row lays its icons out right to left. */
    function drawnChains(): string[] {
      return Array.from(wrapper.findAll('[data-testid=account-chain]'), el => el.attributes('data-chain') ?? '').reverse();
    }

    function overflowChains(): string {
      return wrapper.find('[data-testid=overflow-stub]').text();
    }

    it('should keep them behind the +N even when every chain would fit as an icon', () => {
      setDisabled({ optimism: [ADDRESS] });

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism', 'base'], id: ADDRESS } });

      expect(drawnChains()).toEqual(['eth', 'base']);
      expect(overflowChains()).toBe('optimism');
    });

    it('should list them after the chains that only overflowed for lack of room', () => {
      setDisabled({ eth: [ADDRESS] });

      wrapper = createWrapper({ address: ADDRESS, row: { chains: [...CHAINS, 'avalanche'], id: ADDRESS } });

      expect(drawnChains()).toEqual(['optimism', 'base', 'gnosis', 'polygon_pos', 'arbitrum_one', 'scroll']);
      expect(overflowChains()).toBe('avalanche,eth');
    });

    it('should keep the icon of a single-chain row, which has no +N to hide it behind', () => {
      setDisabled({ eth: [ADDRESS] });

      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth'], id: ADDRESS } });

      expect(drawnChains()).toEqual(['eth']);
      expect(wrapper.find('[data-testid=overflow-stub]').exists()).toBe(false);
    });

    it('should hold a newly skipped chain in place until the menu closes', async () => {
      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism', 'base'], id: ADDRESS } });
      const menu = wrapper.findComponent({ name: 'RuiMenu' });

      menu.vm.$emit('update:modelValue', true);
      await nextTick();
      setDisabled({ eth: [ADDRESS] });
      await nextTick();

      expect(markedChains()).toEqual(['eth']);
      expect(drawnChains()).toEqual(['eth', 'optimism', 'base']);

      menu.vm.$emit('update:modelValue', false);
      await nextTick();

      expect(drawnChains()).toEqual(['optimism', 'base']);
      expect(overflowChains()).toBe('eth');
    });

    it('should hold a chain resumed from the +N menu behind it until that menu closes', async () => {
      setDisabled({ eth: [ADDRESS] });
      wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism', 'base'], id: ADDRESS } });
      const overflow = wrapper.findComponent({ name: 'AccountChainsOverflow' });

      overflow.vm.$emit('update:open', true);
      await nextTick();
      setDisabled({});
      await nextTick();

      expect(overflowChains()).toBe('eth');

      overflow.vm.$emit('update:open', false);
      await nextTick();

      expect(drawnChains()).toEqual(['eth', 'optimism', 'base']);
    });
  });

  it('should not mark a chain the row merely filtered out of its totals', async () => {
    wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth', 'optimism'], id: ADDRESS } });

    await wrapper.find('[data-chain=eth][data-testid=account-chain]').trigger('click');

    expect(wrapper.emitted('update:chainFilter')).toBeDefined();
    expect(markedChains()).toEqual([]);
  });

  describe('the display filter', () => {
    async function clickChain(chain: string): Promise<void> {
      await wrapper.find(`[data-chain=${chain}][data-testid=account-chain]`).trigger('click');
    }

    function isFilter(value: unknown): value is Record<string, string[]> {
      return typeof value === 'object' && value !== null;
    }

    function lastFilter(): Record<string, string[]> | undefined {
      const payload = wrapper.emitted('update:chainFilter')?.at(-1)?.[0];
      return isFilter(payload) ? payload : undefined;
    }

    it('should exclude a chain the row shows', async () => {
      wrapper = createWrapper({ row: { chains: ['eth', 'optimism'], id: 'row-1' } });

      await clickChain('eth');

      expect(lastFilter()).toEqual({ 'row-1': ['eth'] });
    });

    it('should drop the row from the filter once its last exclusion goes', async () => {
      wrapper = createWrapper({ row: { chains: ['eth', 'optimism'], id: 'row-1' } });
      await clickChain('eth');
      await wrapper.setProps({ chainFilter: { 'row-1': ['eth'] } });

      await clickChain('eth');

      expect(lastFilter()).toEqual({});
    });

    it('should keep the other exclusions when one chain comes back', async () => {
      wrapper = createWrapper({ row: { chains: ['eth', 'optimism', 'base'], id: 'row-1' } });
      await wrapper.setProps({ chainFilter: { 'row-1': ['eth', 'base'] } });

      await clickChain('eth');

      expect(lastFilter()).toEqual({ 'row-1': ['base'] });
    });

    it('should leave a single-chain row alone, having nothing to filter against', async () => {
      wrapper = createWrapper({ row: { chains: ['eth'], id: 'row-1' } });

      await clickChain('eth');

      expect(wrapper.emitted('update:chainFilter')).toBeUndefined();
    });

    it('should clear every exclusion of the row at once', async () => {
      wrapper = createWrapper({ row: { chains: ['eth', 'optimism'], id: 'row-1' } });
      await wrapper.setProps({ chainFilter: { 'row-1': ['eth'] } });

      await wrapper.find('[data-testid=account-chain-filter-clear]').trigger('click');

      expect(lastFilter()).toEqual({ 'row-1': [] });
    });
  });
});
