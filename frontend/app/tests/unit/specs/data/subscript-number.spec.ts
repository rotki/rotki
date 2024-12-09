import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { BigNumber, bigNumberify } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';

describe('amountDisplay subscript', () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    const frontendStore = useFrontendSettingsStore();
    frontendStore.update({
      ...frontendStore.settings,
      subscriptDecimals: true,
      thousandSeparator: ',',
      decimalSeparator: '.',
      abbreviateNumber: false,
      amountRoundingMode: BigNumber.ROUND_HALF_UP,
      valueRoundingMode: BigNumber.ROUND_HALF_UP,
    });
  });

  it('shows correct subscript count for small numbers', () => {
    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 10,
    });

    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('0.0000000815'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(true);
    expect(subscriptElement.text()).toBe('7');
  });

  it('shows correct subscript count for very small numbers', () => {
    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 10,
    });

    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('0.000000000123'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(true);
    expect(subscriptElement.text()).toBe('9');
  });

  it('handles regular numbers without subscript', () => {
    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('1.23'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(false);
  });

  it('respects disabled subscript setting', () => {
    const frontendStore = useFrontendSettingsStore();
    frontendStore.update({
      ...frontendStore.settings,
      subscriptDecimals: false,
    });

    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('0.0000000815'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(false);
  });

  it('shows no subscript for number with only 1 leading zero', () => {
    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 10,
    });

    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('0.0123'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(false);
  });

  it('shows no subscript for numbers greater than or equal to 1', () => {
    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 10,
    });

    const wrapper = mount(AmountDisplay, {
      props: {
        value: bigNumberify('1.000000000123'),
        noScramble: true,
        noTruncate: true,
        fiatCurrency: null,
        showCurrency: 'none',
        forceCurrency: true,
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
    expect(subscriptElement.exists()).toBe(false);
  });
});
