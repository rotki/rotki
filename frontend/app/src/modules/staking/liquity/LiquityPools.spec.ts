import { bigNumberify, type LiquityPoolDetailEntry } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LiquityPools from '@/modules/staking/liquity/LiquityPools.vue';

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

function pool(): LiquityPoolDetailEntry {
  const balance = (asset: string, amount: number): { amount: ReturnType<typeof bigNumberify>; asset: string; value: ReturnType<typeof bigNumberify> } => ({
    amount: bigNumberify(amount),
    asset,
    value: bigNumberify(amount),
  });

  return {
    deposited: balance('LUSD', 500),
    gains: balance('ETH', 1),
    rewards: balance('LQTY', 5),
  };
}

describe('modules/staking/liquity/LiquityPools', () => {
  let wrapper: VueWrapper<InstanceType<typeof LiquityPools>>;

  function mountComponent(poolValue: LiquityPoolDetailEntry | null): VueWrapper<InstanceType<typeof LiquityPools>> {
    return mount(LiquityPools, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: { BalanceDisplay: BalanceDisplayStub },
      },
      props: { pool: poolValue },
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

  it('should show no balances without a pool position', () => {
    wrapper = mountComponent(null);

    expect(wrapper.findComponent(BalanceDisplayStub).exists()).toBe(false);
  });

  it('should show the deposit, the rewards and the liquidation gains', () => {
    wrapper = mountComponent(pool());

    const balances = wrapper.findAllComponents(BalanceDisplayStub);
    expect(balances).toHaveLength(3);
    expect(balances.map(item => item.props('asset'))).toEqual(['LUSD', 'LQTY', 'ETH']);
  });

  it('should pass the pool activity through as the loading state', () => {
    isActive.current = true;

    wrapper = mountComponent(pool());

    expect(wrapper.findComponent(BalanceDisplayStub).props('loading')).toBe(true);
  });
});
