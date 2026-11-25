import type { useApiKeyNotice } from '@/modules/accounts/management/use-api-key-notice';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import EthStakingHeaderActions from '@/modules/staking/eth/components/EthStakingHeaderActions.vue';

vi.mock('@/modules/accounts/management/use-api-key-notice', async () => {
  const { computed } = await import('vue');
  return {
    useApiKeyNotice: (): ReturnType<typeof useApiKeyNotice> => ({
      dismiss: vi.fn(async (): Promise<void> => {}),
      dismissed: computed<boolean>(() => false),
    }),
  };
});

const stubs = {
  ModuleSettingsMenu: { template: '<div><slot /></div>' },
  StakingRefreshActions: {
    emits: ['refresh'],
    props: { refreshing: Boolean },
    template: '<button data-testid="refresh-stub" :data-refreshing="String(refreshing)" @click="$emit(\'refresh\')"><slot /></button>',
  },
};

function createWrapper(props: { queryingEvents?: boolean; refreshing?: boolean } = {}): VueWrapper {
  return mount(EthStakingHeaderActions, {
    global: { stubs },
    props: { chainName: 'Ethereum', queryingEvents: false, refreshing: false, syncingHistory: false, ...props },
  });
}

describe('modules/staking/eth/components/EthStakingHeaderActions', () => {
  it('should note staking events queried outside its refresh, without spinning the refresh', () => {
    const wrapper = createWrapper({ queryingEvents: true });

    expect(wrapper.find('[data-testid=eth-staking-querying-events]').text()).toBe('staking_page.eth.querying_events');
    expect(wrapper.find('[data-testid=refresh-stub]').attributes('data-refreshing')).toBe('false');
  });

  it('should show no note while no staking events are queried', () => {
    expect(createWrapper({ refreshing: true }).find('[data-testid=eth-staking-querying-events]').exists()).toBe(false);
  });

  it('should announce the note through a status region that is there before the query starts', async () => {
    const wrapper = createWrapper();
    const status = wrapper.find('[data-testid=eth-staking-querying-events-status]');

    expect(status.attributes('role')).toBe('status');
    expect(status.text()).toBe('');

    await wrapper.setProps({ queryingEvents: true });

    const announced = wrapper.find('[data-testid=eth-staking-querying-events-status]');
    expect(announced.element).toBe(status.element);
    expect(announced.text()).toBe('staking_page.eth.querying_events');
  });

  it('should pass the refresh press on', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=refresh-stub]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });
});
