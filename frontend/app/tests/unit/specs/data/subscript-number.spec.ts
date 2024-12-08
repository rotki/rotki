import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { BigNumber, bigNumberify } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';

describe('amountdisplay subscript', () => {
  beforeEach(() => {
    const pinia = createPinia();
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

  it('shows subscript for very small numbers', () => {
    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 8,
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
        plugins: [createPinia()],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const amount = wrapper.find('[data-cy="display-amount"]');
    expect(amount.attributes('tooltip')).toBe('0.0000000815');
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
        plugins: [createPinia()],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const amount = wrapper.find('[data-cy="display-amount"]');
    expect(amount.text()).toBe('1.23');
  });

  it('respects disabled subscript setting', () => {
    const frontendStore = useFrontendSettingsStore();
    frontendStore.update({
      ...frontendStore.settings,
      subscriptDecimals: false,
    });

    const generalStore = useGeneralSettingsStore();
    generalStore.update({
      ...generalStore.settings,
      uiFloatingPrecision: 8,
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
        plugins: [createPinia()],
        stubs: {
          CopyTooltip: { template: '<div><slot /></div>' },
          RuiTooltip: { template: '<div><slot /></div>' },
        },
      },
    });

    const amount = wrapper.find('[data-cy="display-amount"]');
    expect(amount.attributes('tooltip')).toBe('0.0000000815');
  });
});
