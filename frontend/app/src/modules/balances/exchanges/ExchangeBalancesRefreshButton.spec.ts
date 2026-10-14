import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ExchangeBalancesRefreshButton from '@/modules/balances/exchanges/ExchangeBalancesRefreshButton.vue';

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: vi.fn(() => ({ getExchangeName: (exchange: string): string => `name:${exchange}` })),
}));

const stubs = {
  ExchangeRefreshMenuItem: {
    emits: ['refresh'],
    props: { exchange: { required: true, type: String } },
    template: '<button data-testid="refresh-exchange-menu-item" :data-exchange="exchange" @click="$emit(\'refresh\', exchange)" />',
  },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="tooltip"><slot /></span></div>' },
};

function createWrapper(props: { exchanges?: string[]; selected?: string; loading?: boolean } = {}): VueWrapper<InstanceType<typeof ExchangeBalancesRefreshButton>> {
  return mount(ExchangeBalancesRefreshButton, {
    global: { stubs },
    props: { exchanges: ['kraken', 'binance'], ...props },
  });
}

async function openMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=refresh-exchange-balances-menu]').trigger('click');
  expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');
}

describe('modules/balances/exchanges/ExchangeBalancesRefreshButton', () => {
  it('should ask for a refresh from the main button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-exchange-balances]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });

  it('should say every exchange is refreshed when none is selected', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=tooltip]').text()).toBe('exchange_balances.refresh_menu.all');
  });

  it('should name the selected exchange in the tooltip', () => {
    const wrapper = createWrapper({ selected: 'kraken' });

    expect(wrapper.find('[data-testid=tooltip]').text()).toBe('exchange_balances.refresh_menu.exchange::name:kraken');
  });

  it('should refresh every exchange from the menu and close it', async () => {
    const wrapper = createWrapper({ selected: 'kraken' });
    await openMenu(wrapper);
    await wrapper.find('[data-testid=refresh-exchange-menu-all]').trigger('click');

    expect(wrapper.emitted('refresh-all')).toEqual([[]]);
    expect(wrapper.emitted('refresh')).toBeUndefined();
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should list each exchange in the menu and refresh the one picked', async () => {
    const wrapper = createWrapper();
    await openMenu(wrapper);
    const items = wrapper.findAll('[data-testid=refresh-exchange-menu-item]');

    expect(items.map(item => item.attributes('data-exchange'))).toEqual(['kraken', 'binance']);

    await items[1].trigger('click');

    expect(wrapper.emitted('refresh-exchange')).toEqual([['binance']]);
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should disable both halves without exchanges', () => {
    const wrapper = createWrapper({ exchanges: [] });

    expect(wrapper.find('[data-testid=refresh-exchange-balances]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=refresh-exchange-balances-menu]').attributes('disabled')).toBeDefined();
  });

  it('should spin the main button and hold off refresh all while loading', () => {
    const wrapper = createWrapper({ loading: true });

    expect(wrapper.find('[data-testid=refresh-exchange-balances]').attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-testid=refresh-exchange-menu-all]').attributes('disabled')).toBeDefined();
  });
});
