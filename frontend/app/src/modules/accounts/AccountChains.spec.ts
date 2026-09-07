import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import AccountChains from '@/modules/accounts/AccountChains.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

describe('modules/accounts/AccountChains', () => {
  const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

  let wrapper: VueWrapper;

  function setDisabled(value: Record<string, string[]>): void {
    const store = useSettingsRepo();
    store.updateGeneral({ ...store.general, disabledChainQueries: value });
  }

  function createWrapper(props: { address?: string; row: { chains: string[]; id: string } }): VueWrapper {
    return mount(AccountChains, {
      global: {
        stubs: {
          ChainIcon: true,
          RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
        },
      },
      props: { chainFilter: {}, ...props },
    });
  }

  function markedChains(): string[] {
    return Array.from(wrapper.findAll('[data-testid=account-chain-skipped]'), el => el.attributes('data-chain') ?? '');
  }

  beforeEach(() => {
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

  it('should say why the chain is marked, in place of the bare chain name', () => {
    setDisabled({ eth: [ADDRESS] });

    wrapper = createWrapper({ address: ADDRESS, row: { chains: ['eth'], id: ADDRESS } });

    expect(wrapper.find('[data-testid=account-chain-skipped-tooltip]').text())
      .toContain('account_balances.skip_queries.chain_marker');
    const tooltip = wrapper.find('[data-testid=account-chain-skipped-tooltip]').element.parentElement;
    expect(tooltip?.textContent?.replace('lu-ban', '').trim()).toBe('account_balances.skip_queries.chain_marker::Eth');
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
