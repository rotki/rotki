import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { RuiAlert } from '@rotki/ui-library';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import BinanceHistoryStartDate from '@/modules/settings/api-keys/exchange/BinanceHistoryStartDate.vue';
import ExchangeKeysForm from '@/modules/settings/api-keys/exchange/ExchangeKeysForm.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import '@test/i18n';

describe('exchange-keys-form', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof ExchangeKeysForm>>;

  function createWrapper(overrides: Partial<ExchangeFormData> = {}): VueWrapper<InstanceType<typeof ExchangeKeysForm>> {
    return shallowMount(ExchangeKeysForm, {
      global: {
        plugins: [pinia],
        stubs: {
          I18nT: { template: '<span><slot name="csvImport" /></span>' },
        },
      },
      props: {
        errorMessages: {},
        modelValue: {
          apiKey: '',
          apiSecret: '',
          binanceMarkets: ['BTCUSDT'],
          location: 'binance',
          mode: 'add',
          name: 'Binance 1',
          passphrase: '',
          ...overrides,
        },
        stateUpdated: false,
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should link to the Binance CSV import when adding Binance', () => {
    wrapper = createWrapper();
    expect(wrapper.findComponent(InternalLink).props('to')).toEqual({
      name: '/import/',
      query: { source: 'binance' },
    });
  });

  it('should show an editable Binance history start date', () => {
    wrapper = createWrapper();
    expect(wrapper.findComponent(BinanceHistoryStartDate).exists()).toBe(true);
  });

  it('should combine the Binance notices into one warning', () => {
    wrapper = createWrapper();
    const alerts = wrapper.findAllComponents(RuiAlert);
    expect(alerts).toHaveLength(1);
    expect(alerts[0].props('type')).toBe('warning');
  });

  it('should not show the CSV import link when editing Binance', () => {
    wrapper = createWrapper({ mode: 'edit', newName: 'Binance 1' });
    expect(wrapper.findComponent(InternalLink).exists()).toBe(false);
  });

  it('should use the Binance CSV import history for Binance US', () => {
    wrapper = createWrapper({ location: 'binanceus' });
    expect(wrapper.findComponent(InternalLink).props('to')).toEqual({
      name: '/import/',
      query: { source: 'binance' },
    });
    expect(wrapper.findComponent(BinanceHistoryStartDate).exists()).toBe(true);
  });
});
