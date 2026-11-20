import { type BigNumber, bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReconciliationAmount from '@/modules/history/reconciliation/components/ReconciliationAmount.vue';

const { shouldShowAmount } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { shouldShowAmount: ref<boolean>(true) };
});

vi.mock('@/modules/assets/amount-display', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useAmountDisplaySettings: (): Record<string, unknown> => ({ shouldShowAmount }),
  };
});

function mountAmount(props: {
  amount: BigNumber | null;
  asset?: string;
  noCollectionParent?: boolean;
  signed?: boolean;
}): VueWrapper {
  return mount(ReconciliationAmount, {
    global: {
      plugins: [createPinia()],
      stubs: {
        AssetAmountDisplay: {
          props: ['amount', 'asset', 'noCollectionParent'],
          template: '<span data-testid="amount" :data-asset="asset" :data-no-collection-parent="String(Boolean(noCollectionParent))">{{ amount.toFixed() }}</span>',
        },
      },
    },
    props,
  });
}

describe('reconciliation amount', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(shouldShowAmount, true);
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

  it('should omit the leading plus sign when privacy mode hides amounts', () => {
    set(shouldShowAmount, false);
    const wrapper = mountAmount({ amount: bigNumberify('195.9'), signed: true });

    expect(wrapper.text()).not.toContain('+');
  });

  it('should leave a negative value with its own sign', () => {
    const wrapper = mountAmount({ amount: bigNumberify('-1.88'), signed: true });

    expect(wrapper.text()).not.toContain('+');
    expect(wrapper.text()).toContain('-1.88');
  });

  it('should forward asset and noCollectionParent to AssetAmountDisplay', () => {
    const wrapper = mountAmount({
      amount: bigNumberify('5'),
      asset: 'ETH',
      noCollectionParent: true,
    });

    const amount = wrapper.get('[data-testid="amount"]');
    expect(amount.attributes('data-asset')).toBe('ETH');
    expect(amount.attributes('data-no-collection-parent')).toBe('true');
  });
});
