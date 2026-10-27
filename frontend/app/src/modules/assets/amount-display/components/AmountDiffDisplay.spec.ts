import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import AmountDiffDisplay from '@/modules/assets/amount-display/components/AmountDiffDisplay.vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';

describe('amountDiffDisplay', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('EUR'), uiFloatingPrecision: 2 });
  });

  function createWrapper(amount: string, reference: string, decimals?: number): VueWrapper {
    return mount(AmountDiffDisplay, {
      global: { plugins: [pinia] },
      props: { amount: bigNumberify(amount), decimals, reference: bigNumberify(reference) },
    });
  }

  it('should emphasise the digits from where the amount stops matching the reference', () => {
    const wrapper = createWrapper('0.100412135185230566', '0.100411633744152674', 18);

    expect(wrapper.get('[data-testid=amount-diff-shared]').text()).toBe('0.10041');
    expect(wrapper.get('[data-testid=amount-diff-rest]').text()).toBe('2135185230566');
    expect(wrapper.get('[data-testid=amount-diff-display]').element.textContent).toBe('0.100412135185230566');
  });

  it('should render plainly when the amounts differ from their first significant digit', () => {
    const wrapper = createWrapper('0.100410491601209710', '0.090409712150987558', 18);

    expect(wrapper.find('[data-testid=amount-diff-rest]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=amount-diff-display]').element.textContent).toBe('0.100410491601209710');
  });

  it('should render plainly when the amounts differ in magnitude, even if their strings share a digit', () => {
    const wrapper = createWrapper('12.5', '1.25', 2);

    expect(wrapper.find('[data-testid=amount-diff-rest]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=amount-diff-display]').element.textContent).toBe('12.50');
  });

  it('should render an amount equal to its reference without emphasis', () => {
    const wrapper = createWrapper('0.100412281520505676', '0.100412281520505676', 18);

    expect(wrapper.find('[data-testid=amount-diff-rest]').exists()).toBe(false);
    expect(wrapper.text()).toBe('0.100412281520505676');
  });

  it('should compare the formatted strings, so pinned precision decides where they differ', () => {
    const wrapper = createWrapper('1.004', '1.009', 2);

    expect(wrapper.find('[data-testid=amount-diff-rest]').exists()).toBe(false);
    expect(wrapper.text()).toBe('1.01');
  });
});
