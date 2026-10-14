import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import StakingRefreshActions from '@/modules/staking/components/StakingRefreshActions.vue';

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiIcon: true,
  RuiMenu: {
    template: '<div><slot name="activator" :attrs="{}" /><div data-testid="menu-content"><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="tooltip"><slot /></span></div>' },
};

function createWrapper(syncingHistory = false): VueWrapper<InstanceType<typeof StakingRefreshActions>> {
  return mount(StakingRefreshActions, {
    global: { stubs },
    props: { chainName: 'Ethereum', refreshing: false, syncingHistory, testIdPrefix: 'liquity', tooltip: 'What Refresh covers' },
    slots: { default: '<span data-testid="settings" />' },
  });
}

describe('modules/staking/components/StakingRefreshActions', () => {
  it('should ask for a refresh from the main button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=liquity-refresh]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
    expect(wrapper.emitted('sync-history')).toBeUndefined();
  });

  it('should ask for the full history sync from its menu', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=liquity-sync-history]').trigger('click');

    expect(wrapper.emitted('sync-history')).toEqual([[]]);
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should not offer the sync again while one is running', () => {
    const wrapper = createWrapper(true);

    expect(wrapper.find('[data-testid=liquity-sync-history]').attributes('disabled')).toBeDefined();
  });

  it('should explain what Refresh covers and keep the page settings beside it', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=tooltip]').text()).toBe('What Refresh covers');
    expect(wrapper.find('[data-testid=settings]').exists()).toBe(true);
  });
});
