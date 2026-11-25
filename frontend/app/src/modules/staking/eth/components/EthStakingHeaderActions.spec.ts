import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import EthStakingHeaderActions from '@/modules/staking/eth/components/EthStakingHeaderActions.vue';

vi.mock('@/modules/accounts/management/use-api-key-notice', async () => {
  const { computed } = await import('vue');
  return {
    useApiKeyNotice: (): object => ({ dismiss: vi.fn(), dismissed: computed<boolean>(() => false) }),
  };
});

const stubs = {
  AccountFormApiKeyOffer: true,
  ModuleSettingsMenu: { template: '<div><slot /></div>' },
  RuiProgress: true,
  StakingRefreshActions: {
    emits: ['refresh'],
    props: { refreshing: Boolean },
    template: '<button data-testid="refresh-stub" :data-refreshing="String(refreshing)" @click="$emit(\'refresh\')"><slot /></button>',
  },
};

function createWrapper(props: { queryingEvents?: boolean; refreshing?: boolean } = {}): VueWrapper {
  return mount(EthStakingHeaderActions, {
    global: { stubs },
    props: { chainName: 'Ethereum', refreshing: false, syncingHistory: false, ...props },
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

  it('should pass the refresh press on', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=refresh-stub]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });
});
