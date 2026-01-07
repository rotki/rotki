import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it } from 'vitest';
import { useFiatConversion } from '@/modules/amount-display/composables/use-fiat-conversion';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useCurrencies } from '@/types/currencies';

describe('modules/amount-display/composables/use-fiat-conversion', () => {
  beforeEach(() => {
    setActivePinia(createPinia());

    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('USD') });

    const pricesStore = useBalancePricesStore();
    const { exchangeRates } = storeToRefs(pricesStore);
    set(exchangeRates, {
      EUR: bigNumberify(0.85),
      GBP: bigNumberify(0.73),
    });
  });

  describe('converted', () => {
    it('should return value as-is when no source currency', () => {
      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: '',
        value,
      });

      expect(get(converted).toNumber()).toBe(100);
    });

    it('should return value as-is when source equals target', () => {
      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: 'USD',
        value,
      });

      expect(get(converted).toNumber()).toBe(100);
    });

    it('should return zero when value is undefined', () => {
      const value = ref<undefined>(undefined);
      const { converted } = useFiatConversion({
        from: 'EUR',
        value,
      });

      expect(get(converted).toNumber()).toBe(0);
    });

    it('should convert EUR to USD correctly', () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('USD') });

      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: 'EUR',
        value,
      });

      // 100 EUR * (1 / 0.85) = ~117.65 USD
      expect(get(converted).toNumber()).toBeCloseTo(117.65, 1);
    });

    it('should convert USD to EUR correctly', () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('EUR') });

      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: 'USD',
        value,
      });

      // 100 USD * 0.85 = 85 EUR
      expect(get(converted).toNumber()).toBe(85);
    });

    it('should convert between non-USD currencies', () => {
      const { findCurrency } = useCurrencies();
      updateGeneralSettings({ mainCurrency: findCurrency('GBP') });

      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: 'EUR',
        value,
      });

      // 100 EUR * (0.73 / 0.85) = ~85.88 GBP
      expect(get(converted).toNumber()).toBeCloseTo(85.88, 1);
    });
  });

  describe('loading', () => {
    it('should return false when no timestamp', () => {
      const value = ref(bigNumberify(100));
      const { loading } = useFiatConversion({
        from: 'EUR',
        value,
      });

      expect(get(loading)).toBe(false);
    });
  });

  describe('reactivity', () => {
    it('should update when value changes', () => {
      const value = ref(bigNumberify(100));
      const { converted } = useFiatConversion({
        from: 'EUR',
        value,
      });

      const initialValue = get(converted).toNumber();
      set(value, bigNumberify(200));

      expect(get(converted).toNumber()).toBe(initialValue * 2);
    });

    it('should update when from currency changes', () => {
      const value = ref(bigNumberify(100));
      const from = ref<string>('USD');
      const { converted } = useFiatConversion({
        from,
        value,
      });

      expect(get(converted).toNumber()).toBe(100);

      set(from, 'EUR');
      expect(get(converted).toNumber()).toBeCloseTo(117.65, 1);
    });
  });
});
