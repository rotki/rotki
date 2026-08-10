import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ExchangeKeysForm from '@/modules/settings/api-keys/exchange/ExchangeKeysForm.vue';
import '@test/i18n';

/**
 * Which fields an exchange demands is decided entirely by `location` and `mode`, through a handful
 * of predicates over the location store's capability lists. These tests drive the form through its
 * exposed `validate()` rather than through the markup, so they keep their meaning when the rules
 * move to a pure module and when the template is split into per-exchange sub-components.
 */
// Plain state rather than refs: `vi.hoisted` runs before the auto-imported `ref` exists. The store
// is constructed per mount, so setting these before `createWrapper` is enough.
const capabilities = vi.hoisted(() => ({
  locations: new Array<string>(),
  withoutSecret: new Array<string>(),
  withPassphrase: new Array<string>(),
}));

const KNOWN_LOCATIONS = ['binance', 'binanceus', 'bitpanda', 'gate', 'kraken', 'kucoin', 'okx'];

// A real store, not a plain object: the form reads it through `storeToRefs`.
vi.mock('@/modules/core/common/use-location-store', async () => {
  const { defineStore } = await import('pinia');
  const { computed } = await import('vue');
  return {
    useLocationStore: defineStore('location-stub', () => ({
      exchangesWithoutApiSecret: computed(() => capabilities.withoutSecret),
      exchangesWithPassphrase: computed(() => capabilities.withPassphrase),
      // 🔴 Not optional padding: `onMounted` rewrites `name` to `suggestedName(location)` in add
      // mode, and an unknown location yields `''` — which fails the required-name rule and makes
      // every scenario look invalid for the wrong reason. Emptying it models the store before its
      // locations have been fetched.
      tradeLocations: computed(() => capabilities.locations.map(
        identifier => ({ identifier, name: identifier }),
      )),
      useIsExperimentalExchange: (): ComputedRef<boolean> => computed<boolean>(() => false),
    })),
  };
});

describe('settings/api-keys/exchange validation', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof ExchangeKeysForm>>;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
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
          BinanceHistoryStartDate: true,
          BinancePairsSelector: true,
          ExchangeInput: true,
          I18nT: true,
          InternalLink: true,
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

  async function validate(overrides: Partial<ExchangeFormData> = {}): Promise<boolean> {
    return createWrapper(overrides).vm.validate();
  }

  /**
   * `onMounted` fills the name in — the suggestion when adding, the existing name when editing — so
   * a blank name cannot be produced by the initial props. Clearing it has to happen after mount,
   * which is also the only way a user reaches that state.
   */
  async function validateAfterClearing(
    field: 'name' | 'newName',
    overrides: Partial<ExchangeFormData> = {},
  ): Promise<boolean> {
    const form = createWrapper(overrides);
    await form.setProps({ modelValue: { ...form.props('modelValue'), [field]: '' } });
    return form.vm.validate();
  }

  describe('the common fields', () => {
    it('should accept a complete form', async () => {
      await expect(validate()).resolves.toBe(true);
    });

    it('should suggest a name when adding rather than leave it blank', () => {
      const emitted = createWrapper({ name: '' }).emitted('update:modelValue');
      expect(emitted?.at(-1)?.[0]).toMatchObject({ name: 'kucoin 1' });
    });

    it('should require a name when adding', async () => {
      await expect(validateAfterClearing('name')).resolves.toBe(false);
    });

    /**
     * The locations arrive from the backend, so the store holds none until that fetch lands. The
     * suggestion runs once in `onMounted`, so writing an empty one over the given name leaves the
     * field blank with nothing to restore it.
     */
    it('should keep the given name when the locations have not loaded', async () => {
      capabilities.locations = [];

      await expect(validate({ name: 'Kucoin 1' })).resolves.toBe(true);
    });

    it('should require an api key', async () => {
      await expect(validate({ apiKey: '' })).resolves.toBe(false);
    });

    it('should require an api secret', async () => {
      await expect(validate({ apiSecret: '' })).resolves.toBe(false);
    });
  });

  describe('the per exchange capabilities', () => {
    it('should not require a secret for an exchange that has none', async () => {
      capabilities.withoutSecret = ['bitpanda'];

      await expect(validate({ apiSecret: '', location: 'bitpanda' })).resolves.toBe(true);
    });

    it('should still require a secret for an exchange that has one', async () => {
      capabilities.withoutSecret = ['bitpanda'];

      await expect(validate({ apiSecret: '', location: 'kucoin' })).resolves.toBe(false);
    });

    it('should require the passphrase for an exchange that uses one', async () => {
      capabilities.withPassphrase = ['kucoin'];

      await expect(validate({ passphrase: '' })).resolves.toBe(false);
    });

    it('should accept the passphrase once given', async () => {
      capabilities.withPassphrase = ['kucoin'];

      await expect(validate({ passphrase: 'phrase' })).resolves.toBe(true);
    });

    it('should not require a passphrase for an exchange that has none', async () => {
      await expect(validate({ passphrase: '' })).resolves.toBe(true);
    });
  });

  describe('editing an existing exchange', () => {
    const edit: Partial<ExchangeFormData> = { mode: 'edit', name: 'Kucoin 1', newName: 'Kucoin 1' };

    it('should seed the new name from the existing one', () => {
      const emitted = createWrapper({ ...edit, newName: '' }).emitted('update:modelValue');
      expect(emitted?.at(-1)?.[0]).toMatchObject({ newName: 'Kucoin 1' });
    });

    it('should require the new name', async () => {
      await expect(validateAfterClearing('newName', edit)).resolves.toBe(false);
    });

    it('should not demand the keys again while they stay masked', async () => {
      await expect(validate({ ...edit, apiKey: '', apiSecret: '' })).resolves.toBe(true);
    });
  });

  describe('the kraken futures pair', () => {
    const kraken: Partial<ExchangeFormData> = { location: 'kraken', name: 'Kraken 1' };

    it('should accept neither futures credential', async () => {
      await expect(validate(kraken)).resolves.toBe(true);
    });

    it('should accept both futures credentials', async () => {
      await expect(validate({
        ...kraken,
        krakenFuturesApiKey: 'fkey',
        krakenFuturesApiSecret: 'fsecret',
      })).resolves.toBe(true);
    });

    it('should reject a futures key with no futures secret', async () => {
      await expect(validate({ ...kraken, krakenFuturesApiKey: 'fkey' })).resolves.toBe(false);
    });

    it('should reject a futures secret with no futures key', async () => {
      await expect(validate({ ...kraken, krakenFuturesApiSecret: 'fsecret' })).resolves.toBe(false);
    });
  });

  describe('the region selectors', () => {
    it('should require the gate region', async () => {
      await expect(validate({ location: 'gate', name: 'Gate 1' })).resolves.toBe(false);
    });

    it('should accept a chosen gate region', async () => {
      await expect(validate({ gateLocation: 'global', location: 'gate', name: 'Gate 1' })).resolves.toBe(true);
    });

    it('should require the okx region', async () => {
      await expect(validate({ location: 'okx', name: 'Okx 1' })).resolves.toBe(false);
    });

    it('should accept a chosen okx region', async () => {
      await expect(validate({ location: 'okx', name: 'Okx 1', okxLocation: 'global' })).resolves.toBe(true);
    });
  });

  describe('binance', () => {
    const binance: Partial<ExchangeFormData> = {
      binanceHistoryStartTs: 1700000000,
      binanceMarkets: ['BTCUSDT'],
      location: 'binance',
      name: 'Binance 1',
    };

    it('should accept binance with markets and a start date', async () => {
      await expect(validate(binance)).resolves.toBe(true);
    });

    it('should require the markets', async () => {
      await expect(validate({ ...binance, binanceMarkets: [] })).resolves.toBe(false);
    });

    it('should require the history start date when adding', async () => {
      await expect(validate({ ...binance, binanceHistoryStartTs: undefined })).resolves.toBe(false);
    });

    // `showBinanceHistoryImport` is `isBinance && !editMode`, so the date is only demanded while
    // adding — an existing connection already has its history.
    it('should not require the history start date when editing', async () => {
      await expect(validate({
        ...binance,
        binanceHistoryStartTs: undefined,
        mode: 'edit',
        newName: 'Binance 1',
      })).resolves.toBe(true);
    });
  });
});
