import { type BigNumber, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import ReconciliationAmount from '@/modules/history/reconciliation/components/ReconciliationAmount.vue';

vi.mock('@/modules/assets/amount-display', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useAmountDisplaySettings: (): Record<string, unknown> => ({ shouldShowAmount: computed(() => true) }),
  };
});

function mountAmount(props: { amount: BigNumber | null; signed?: boolean }): VueWrapper {
  return mount(ReconciliationAmount, {
    global: {
      plugins: [createPinia()],
      stubs: {
        AssetAmountDisplay: {
          props: ['amount'],
          template: '<span data-testid="amount">{{ amount.toFixed() }}</span>',
        },
      },
    },
    props,
  });
}

describe('reconciliation amount', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show an unavailable mark for a null amount instead of a zero', () => {
    const wrapper = mountAmount({ amount: null });

    expect(wrapper.find('[data-testid="reconciliation-amount-unavailable"]').exists()).toBe(true);
  });

  it('should sign a positive difference explicitly', () => {
    const wrapper = mountAmount({ amount: bigNumberify('195.9'), signed: true });

    expect(wrapper.text()).toContain('+');
    expect(wrapper.text()).toContain('195.9');
  });

  it('should leave a negative value with its own sign', () => {
    const wrapper = mountAmount({ amount: bigNumberify('-1.88'), signed: true });

    expect(wrapper.text()).not.toContain('+');
    expect(wrapper.text()).toContain('-1.88');
  });
});
