import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { RuiAlert } from '@rotki/ui-library';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import BinancePairsSelector from '@/modules/settings/api-keys/BinancePairsSelector.vue';
import BinanceHistoryStartDate from '@/modules/settings/api-keys/exchange/BinanceHistoryStartDate.vue';
import ExchangeKeysForm from '@/modules/settings/api-keys/exchange/ExchangeKeysForm.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import '@test/i18n';

/**
 * Which sections the form renders is decided by the exchange and the mode, through the same
 * predicates that decide what it validates. The validation spec deliberately asserts nothing about
 * structure so that it survives a refactor, which leaves this as the net for the template: every
 * conditional section, checked per exchange, so moving one into a sub-component cannot quietly drop
 * it or wire it to the wrong exchange.
 */
const capabilities = vi.hoisted(() => ({
  experimental: false,
  locations: new Array<string>(),
  withoutSecret: new Array<string>(),
  withPassphrase: new Array<string>(),
}));

const KNOWN_LOCATIONS = ['binance', 'binanceus', 'bitpanda', 'bybit', 'cryptocom', 'gate', 'htx', 'kraken', 'kucoin', 'okx'];

vi.mock('@/modules/core/common/use-location-store', async () => {
  const { defineStore } = await import('pinia');
  const { computed } = await import('vue');
  return {
    useLocationStore: defineStore('location-stub', () => ({
      exchangesWithoutApiSecret: computed(() => capabilities.withoutSecret),
      exchangesWithPassphrase: computed(() => capabilities.withPassphrase),
      tradeLocations: computed(() => capabilities.locations.map(
        identifier => ({ identifier, name: identifier }),
      )),
      useIsExperimentalExchange: (): ComputedRef<boolean> => computed<boolean>(() => capabilities.experimental),
    })),
  };
});

describe('settings/api-keys/exchange rendering', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof ExchangeKeysForm>>;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    capabilities.experimental = false;
    capabilities.locations = [...KNOWN_LOCATIONS];
    capabilities.withoutSecret = [];
    capabilities.withPassphrase = [];
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(overrides: Partial<ExchangeFormData> = {}): VueWrapper<InstanceType<typeof ExchangeKeysForm>> {
    wrapper = mount(ExchangeKeysForm, {
      global: {
        plugins: [pinia],
        stubs: {
          ExchangeInput: true,
          I18nT: { template: '<span><slot name="csvImport" /></span>' },
          // `InternalLink` renders a `RouterLink` with a scoped slot, which needs a real router.
          RouterLink: true,
        },
      },
      props: {
        errorMessages: {},
        modelValue: {
          apiKey: 'key',
          apiSecret: 'secret',
          binanceMarkets: [],
          location: 'kucoin',
          mode: 'add',
          name: 'Kucoin 1',
          passphrase: '',
          ...overrides,
        },
        stateUpdated: false,
      },
    });
    return wrapper;
  }

  function has(testId: string): boolean {
    return wrapper.find(`[data-cy=${testId}]`).exists();
  }

  describe('the fields every exchange shows', () => {
    it('should show the name and the api key', () => {
      createWrapper();

      expect(has('name')).toBe(true);
      expect(has('api-key')).toBe(true);
    });

    it('should show the api secret for an exchange that has one', () => {
      createWrapper();

      expect(has('api-secret')).toBe(true);
    });

    it('should hide the api secret for an exchange that has none', () => {
      capabilities.withoutSecret = ['bitpanda'];
      createWrapper({ location: 'bitpanda' });

      expect(has('api-secret')).toBe(false);
    });

    it('should hide the passphrase unless the exchange uses one', () => {
      createWrapper();

      expect(has('passphrase')).toBe(false);
    });

    it('should show the passphrase for an exchange that uses one', () => {
      capabilities.withPassphrase = ['kucoin'];
      createWrapper();

      expect(has('passphrase')).toBe(true);
    });
  });

  describe('the per exchange sections', () => {
    it('should show the kraken account type and futures fields', () => {
      createWrapper({ location: 'kraken', name: 'kraken 1' });

      expect(has('account-type')).toBe(true);
      expect(has('kraken-futures-api-key')).toBe(true);
      expect(has('kraken-futures-api-secret')).toBe(true);
    });

    it('should keep the kraken sections off other exchanges', () => {
      createWrapper();

      expect(has('account-type')).toBe(false);
      expect(has('kraken-futures-api-key')).toBe(false);
      expect(has('kraken-futures-api-secret')).toBe(false);
    });

    it('should show the gate region only for gate', () => {
      createWrapper({ gateLocation: 'global', location: 'gate', name: 'gate 1' });

      expect(has('gate-location')).toBe(true);
      expect(has('okx-location')).toBe(false);
    });

    it('should show the okx region only for okx', () => {
      createWrapper({ location: 'okx', name: 'okx 1', okxLocation: 'global' });

      expect(has('okx-location')).toBe(true);
      expect(has('gate-location')).toBe(false);
    });

    it('should show the binance pairs selector for binance', () => {
      createWrapper({ location: 'binance', name: 'binance 1' });

      expect(wrapper.findComponent(BinancePairsSelector).exists()).toBe(true);
    });

    it('should not show the pairs selector for another exchange', () => {
      createWrapper();

      expect(wrapper.findComponent(BinancePairsSelector).exists()).toBe(false);
    });
  });

  describe('the binance history import', () => {
    it('should offer the csv import and the start date when adding', () => {
      createWrapper({ location: 'binance', name: 'binance 1' });

      expect(wrapper.findComponent(InternalLink).exists()).toBe(true);
      expect(wrapper.findComponent(BinanceHistoryStartDate).exists()).toBe(true);
    });

    it('should offer neither when editing', () => {
      createWrapper({ location: 'binance', mode: 'edit', name: 'binance 1', newName: 'binance 1' });

      expect(wrapper.findComponent(InternalLink).exists()).toBe(false);
      expect(wrapper.findComponent(BinanceHistoryStartDate).exists()).toBe(false);
    });
  });

  describe('the notices', () => {
    function alertTypes(): (string | undefined)[] {
      return wrapper.findAllComponents(RuiAlert).map(alert => alert.props('type'));
    }

    it('should show none for a plain exchange', () => {
      createWrapper();

      expect(alertTypes()).toStrictEqual([]);
    });

    it.each(['kraken', 'coinbase', 'coinbaseprime'])('should warn about the key delay for %s', (location) => {
      capabilities.locations = [...KNOWN_LOCATIONS, location];
      createWrapper({ location, name: `${location} 1` });

      expect(alertTypes()).toContain('info');
    });

    it.each(['bybit', 'htx', 'cryptocom'])('should warn about the history limit for %s', (location) => {
      createWrapper({ location, name: `${location} 1` });

      expect(alertTypes()).toContain('warning');
    });

    it('should flag an experimental exchange', () => {
      capabilities.experimental = true;
      createWrapper();

      expect(alertTypes()).toContain('info');
    });
  });

  describe('the saved keys', () => {
    const edit: Partial<ExchangeFormData> = { mode: 'edit', name: 'Kucoin 1', newName: 'Kucoin 1' };

    function value(testId: string): string {
      return wrapper.find<HTMLInputElement>(`[data-cy=${testId}] input`).element.value;
    }

    it('should mask the saved key and secret while editing', () => {
      createWrapper(edit);

      expect(value('api-key')).toBe('*'.repeat(30));
      expect(value('api-secret')).toBe('*'.repeat(30));
    });

    it('should show what was typed when adding', () => {
      createWrapper();

      expect(value('api-key')).toBe('key');
    });

    it('should mask the saved futures credentials while editing', () => {
      createWrapper({
        ...edit,
        krakenFuturesApiKey: 'fkey',
        krakenFuturesApiSecret: 'fsecret',
        location: 'kraken',
      });

      expect(value('kraken-futures-api-key')).toBe('*'.repeat(30));
    });

    it('should offer no replace toggle while adding', () => {
      createWrapper();

      expect(has('toggle-edit-keys')).toBe(false);
    });

    /**
     * A masked field must not be revealable: there is nothing behind the asterisks to reveal, and
     * offering the eye on a credential the app does not hold is misleading.
     */
    it('should not offer to reveal a masked key', () => {
      createWrapper(edit);

      expect(wrapper.find('[data-cy=api-key]').findComponent({ name: 'RuiRevealableTextField' }).exists())
        .toBe(false);
    });

    it('should offer to reveal a key being typed', () => {
      createWrapper();

      expect(wrapper.find('[data-cy=api-key]').findComponent({ name: 'RuiRevealableTextField' }).exists())
        .toBe(true);
    });

    it('should reveal the field for typing when asked to replace the keys', async () => {
      createWrapper(edit);

      await wrapper.find('[data-cy=toggle-edit-keys]').trigger('click');

      expect(value('api-key')).toBe('key');
    });

    /**
     * The clear happens on the way back, not on the way in: turning the toggle off abandons the
     * replacement, and whatever was typed must not be left behind to be saved.
     */
    it('should drop what was typed when the replacement is abandoned', async () => {
      createWrapper(edit);
      const toggle = wrapper.find('[data-cy=toggle-edit-keys]');

      await toggle.trigger('click');
      await toggle.trigger('click');

      expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
        apiKey: '',
        apiSecret: '',
      });
    });

    it('should drop the futures pair when its replacement is abandoned', async () => {
      createWrapper({ ...edit, location: 'kraken' });
      const toggle = wrapper.find('[data-cy=toggle-edit-futures-keys]');

      await toggle.trigger('click');
      await toggle.trigger('click');

      expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({
        krakenFuturesApiKey: '',
        krakenFuturesApiSecret: '',
      });
    });
  });
});
