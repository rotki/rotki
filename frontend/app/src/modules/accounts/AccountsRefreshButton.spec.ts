import type { ChainRefreshState } from '@/modules/accounts/use-category-chain-refresh';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountsRefreshButton from '@/modules/accounts/AccountsRefreshButton.vue';

const { refreshable, refreshDisabled } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    refreshable: ref<ChainRefreshState[]>([]),
    refreshDisabled: ref<boolean>(false),
  };
});

vi.mock('@/modules/accounts/use-blockchain-account-loading', async () => {
  const { computed } = await import('vue');
  return {
    useBlockchainAccountLoading: (): object => ({
      isSectionLoading: computed<boolean>(() => false),
      refreshDisabled: computed<boolean>(() => get(refreshDisabled)),
    }),
  };
});

vi.mock('@/modules/accounts/use-category-chain-refresh', () => ({
  useCategoryChainRefresh: (): object => ({ refreshable }),
}));

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    template: '<div><span data-testid="menu-activator" @click="$emit(\'update:modelValue\', true)"><slot name="activator" :attrs="{}" /></span><slot /></div>',
  },
};

function chain(id: string): ChainRefreshState {
  return { chain: id, name: `name:${id}`, skipped: false, timestamp: 100 };
}

function createWrapper(slots: Record<string, string> = {}): VueWrapper<InstanceType<typeof AccountsRefreshButton>> {
  return mount(AccountsRefreshButton, { global: { stubs }, props: { category: 'bitcoin' }, slots });
}

async function openMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=menu-activator]').trigger('click');
}

describe('modules/accounts/AccountsRefreshButton', () => {
  beforeEach(() => {
    set(refreshable, [chain('btc'), chain('bch')]);
    set(refreshDisabled, false);
  });

  it('should ask for a refresh of the whole category from the main button', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=blockchain-account-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toStrictEqual([[]]);
  });

  it('should disable the main button while the category refreshes', () => {
    set(refreshDisabled, true);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=blockchain-account-refresh]').attributes('disabled')).toBeDefined();
  });

  it('should offer no options menu when a single chain can be refreshed', () => {
    set(refreshable, [chain('sol')]);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=blockchain-account-refresh-menu]').exists()).toBe(false);
  });

  it('should refresh one chain picked from the options menu', async () => {
    const wrapper = createWrapper();
    await openMenu(wrapper);

    const items = wrapper.findAll('[data-testid=blockchain-account-refresh-chain]');
    expect(items.map(item => item.text())).toStrictEqual(['name:btc', 'name:bch']);

    await items[1].trigger('click');

    expect(wrapper.emitted('refresh')).toStrictEqual([[['bch']]]);
  });

  it('should show a menu of its own in place of the chain list', async () => {
    set(refreshable, [chain('eth')]);
    const wrapper = createWrapper({ menu: '<div data-testid="custom-menu" />' });
    await openMenu(wrapper);

    expect(wrapper.find('[data-testid=custom-menu]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=blockchain-account-refresh-chain]').exists()).toBe(false);
  });
});
