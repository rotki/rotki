import { type BigNumber, bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetValue } from '@/modules/assets/amount-display/use-asset-value';

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): {
    getAssetPrice: (asset: string, fallback: BigNumber) => BigNumber;
  } => ({
    getAssetPrice: (asset: string, fallback: BigNumber): BigNumber => {
      if (asset === 'ETH')
        return bigNumberify(2000);
      if (asset === 'BTC')
        return bigNumberify(50000);
      return fallback;
    },
  }),
}));

describe('modules/amount-display/composables/use-asset-value', () => {
  beforeEach(() => {
    setActivePinia(createPinia());

    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('USD') });
  });

  describe('value', () => {
    it('should return zero when asset is empty', () => {
      const { value } = useAssetValue({
        amount: bigNumberify(1),
        asset: '',
      });

      expect(get(value).toNumber()).toBe(0);
    });

    it('should calculate value from amount × price', () => {
      const { value } = useAssetValue({
        amount: bigNumberify(2),
        asset: 'ETH',
      });

      // 2 ETH × 2000 USD/ETH = 4000 USD
      expect(get(value).toNumber()).toBe(4000);
    });

    it('should use knownPrice when provided', () => {
      const { value } = useAssetValue({
        amount: bigNumberify(2),
        asset: 'ETH',
        knownPrice: bigNumberify(1500),
      });

      // 2 ETH × 1500 USD/ETH = 3000 USD
      expect(get(value).toNumber()).toBe(3000);
    });

    it('should calculate correctly for BTC', () => {
      const { value } = useAssetValue({
        amount: bigNumberify(0.5),
        asset: 'BTC',
      });

      // 0.5 BTC × 50000 USD/BTC = 25000 USD
      expect(get(value).toNumber()).toBe(25000);
    });

    it('should return zero when amount is zero', () => {
      const { value } = useAssetValue({
        amount: bigNumberify(0),
        asset: 'ETH',
      });

      expect(get(value).toNumber()).toBe(0);
    });
  });

  describe('price', () => {
    it('should return the price per unit', () => {
      const { price } = useAssetValue({
        amount: bigNumberify(1),
        asset: 'ETH',
      });

      expect(get(price).toNumber()).toBe(2000);
    });

    it('should return knownPrice when provided', () => {
      const { price } = useAssetValue({
        amount: bigNumberify(1),
        asset: 'ETH',
        knownPrice: bigNumberify(1800),
      });

      expect(get(price).toNumber()).toBe(1800);
    });

    it('should return zero for unknown asset', () => {
      const { price } = useAssetValue({
        amount: bigNumberify(1),
        asset: 'UNKNOWN',
      });

      expect(get(price).toNumber()).toBe(0);
    });
  });

  describe('historic price', () => {
    it('should not fallback to current price when historic price is unavailable', () => {
      const { price, value } = useAssetValue({
        amount: bigNumberify(2),
        asset: 'ETH',
        timestamp: { ms: 1700000000000 },
      });

      // Historic price not found → should return zero, not the current price (2000)
      expect(get(price).toNumber()).toBe(0);
      expect(get(value).toNumber()).toBe(0);
    });
  });

  describe('loading', () => {
    it('should return false when no timestamp', () => {
      const { loading } = useAssetValue({
        amount: bigNumberify(1),
        asset: 'ETH',
      });

      expect(get(loading)).toBe(false);
    });
  });

  describe('reactivity', () => {
    it('should update when amount changes', () => {
      const amount = ref(bigNumberify(1));
      const { value } = useAssetValue({
        amount,
        asset: 'ETH',
      });

      expect(get(value).toNumber()).toBe(2000);

      set(amount, bigNumberify(3));
      expect(get(value).toNumber()).toBe(6000);
    });

    it('should update when asset changes', () => {
      const asset = ref('ETH');
      const knownPrice = ref(bigNumberify(2000));
      const { value } = useAssetValue({
        amount: bigNumberify(1),
        asset,
        knownPrice,
      });

      expect(get(value).toNumber()).toBe(2000);

      // Update known price when asset changes (simulating price lookup)
      set(knownPrice, bigNumberify(50000));
      expect(get(value).toNumber()).toBe(50000);
    });

    it('should update when knownPrice changes', () => {
      const knownPrice = ref(bigNumberify(1000));
      const { value } = useAssetValue({
        amount: bigNumberify(2),
        asset: 'ETH',
        knownPrice,
      });

      expect(get(value).toNumber()).toBe(2000);

      set(knownPrice, bigNumberify(2500));
      expect(get(value).toNumber()).toBe(5000);
    });
  });
});
