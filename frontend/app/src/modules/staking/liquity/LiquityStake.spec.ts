import { bigNumberify, type LiquityStakingDetailEntry } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityStake from '@/modules/staking/liquity/LiquityStake.vue';

const isActive = vi.hoisted(() => ({ current: false }));

vi.mock('@/modules/task-center/use-task-center', async () => {
  const { computed } = await import('vue');
  return {
    useTaskCenter: (): Record<string, unknown> => ({
      useIsActive: () => computed(() => isActive.current),
    }),
  };
});

const BalanceDisplayStub = defineComponent({
  name: 'BalanceDisplayStub',
  props: {
    asset: { default: '', type: String },
    iconSize: { default: '', type: String },
    loading: { default: false, type: Boolean },
    value: { default: null, type: Object },
  },
  template: '<div data-testid="balance" />',
});

function stake(): LiquityStakingDetailEntry {
  const balance = (asset: string, amount: number): { amount: ReturnType<typeof bigNumberify>; asset: string; value: ReturnType<typeof bigNumberify> } => ({
    amount: bigNumberify(amount),
    asset,
    value: bigNumberify(amount),
  });

  return {
    ethRewards: balance('ETH', 1),
    lusdRewards: balance('LUSD', 2),
    staked: balance('LQTY', 100),
  };
}

describe('modules/staking/liquity/LiquityStake', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityStake>>;

  function mountComponent(props: { stake?: LiquityStakingDetailEntry | null } = {}): VueWrapper<InstanceType<typeof LiquityStake>> {
    return mount(LiquityStake, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: { BalanceDisplay: BalanceDisplayStub },
      },
      props,
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    isActive.current = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should say nothing is staked when there is no stake', () => {
    wrapper = mountComponent();

    expect(wrapper.text()).toContain('loan_stake.no_lqty_staked');
    expect(wrapper.findComponent(BalanceDisplayStub).exists()).toBe(false);
  });

  it('should treat an explicit null the same as an absent stake', () => {
    wrapper = mountComponent({ stake: null });

    expect(wrapper.text()).toContain('loan_stake.no_lqty_staked');
  });

  it('should show the staked amount and both reward assets', () => {
    wrapper = mountComponent({ stake: stake() });

    const balances = wrapper.findAllComponents(BalanceDisplayStub);
    expect(balances).toHaveLength(3);
    expect(balances.map(item => item.props('asset'))).toEqual(['LQTY', 'LUSD', 'ETH']);
    expect(wrapper.text()).not.toContain('loan_stake.no_lqty_staked');
  });

  it('should pass the staking activity through as the loading state', () => {
    isActive.current = true;

    wrapper = mountComponent({ stake: stake() });

    expect(wrapper.findComponent(BalanceDisplayStub).props('loading')).toBe(true);
  });
});
