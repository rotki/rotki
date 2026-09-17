import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { type BalanceSource, RefreshSource } from '@/modules/balances/refresh/core/refresh-types';
import DashboardRefreshButton from '@/modules/dashboard/components/DashboardRefreshButton.vue';
import { DashboardRefreshKind } from '@/modules/dashboard/dashboard-refresh-action';

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    template: '<div><slot name="activator" :attrs="{}" /><div data-testid="menu-content"><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /></div>' },
};

function createWrapper(busy = false, sources: BalanceSource[] = []): VueWrapper<InstanceType<typeof DashboardRefreshButton>> {
  return mount(DashboardRefreshButton, { global: { stubs }, props: { busy, sources } });
}

describe('dashboardRefreshButton', () => {
  it('should offer a refresh for each connected source and nothing else', () => {
    const wrapper = createWrapper(false, [RefreshSource.BLOCKCHAIN, RefreshSource.BANKS, RefreshSource.MANUAL]);

    expect(wrapper.find('[data-testid=dashboard-refresh-source-blockchain]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=dashboard-refresh-source-banks]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=dashboard-refresh-source-manual]').text()).toBe('dashboard.refresh.source.manual');
    expect(wrapper.find('[data-testid=dashboard-refresh-source-exchanges]').exists()).toBe(false);
  });

  it('should hide the source section when nothing is connected', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid^=dashboard-refresh-source-]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('dashboard.refresh.source.title');
  });

  it('should list the refresh modes in order', () => {
    const wrapper = createWrapper();
    const modes = wrapper.findAll('[data-testid=menu-content] button').map(button => button.attributes('data-testid'));

    expect(modes).toEqual(['dashboard-refresh-balances', 'dashboard-refresh-redetect', 'dashboard-refresh-prices']);
  });

  it('should ask to refresh balances when the main button is clicked', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=dashboard-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[{ kind: DashboardRefreshKind.BALANCES }]]);
  });

  it.each([
    { kind: DashboardRefreshKind.BALANCES, testId: 'dashboard-refresh-balances' },
    { kind: DashboardRefreshKind.REDETECT, testId: 'dashboard-refresh-redetect' },
    { kind: DashboardRefreshKind.PRICES, testId: 'dashboard-refresh-prices' },
  ])('should ask for $kind from its menu item', async ({ kind, testId }) => {
    const wrapper = createWrapper();
    await wrapper.find(`[data-testid=${testId}]`).trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[{ kind }]]);
  });

  it('should ask to refresh the chosen source', async () => {
    const wrapper = createWrapper(false, [RefreshSource.BLOCKCHAIN, RefreshSource.EXCHANGES]);
    await wrapper.find('[data-testid=dashboard-refresh-source-exchanges]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[{ kind: DashboardRefreshKind.SOURCE, source: RefreshSource.EXCHANGES }]]);
  });

  it('should disable both the button and the menu while a refresh is running', () => {
    const wrapper = createWrapper(true);

    expect(wrapper.find('[data-testid=dashboard-refresh]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=dashboard-refresh-menu]').attributes('disabled')).toBeDefined();
  });

  it('should keep both enabled when idle', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=dashboard-refresh]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid=dashboard-refresh-menu]').attributes('disabled')).toBeUndefined();
  });
});
