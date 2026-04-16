import { bigNumberify } from '@rotki/common';
import { beforeAll, describe, expect, it } from 'vitest';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';

describe('usePriceUtils', () => {
  let store: ReturnType<typeof useBalancePricesStore>;
  let utils: ReturnType<typeof usePriceUtils>;

  beforeAll(() => {
    setActivePinia(createPinia());
    store = useBalancePricesStore();
    utils = usePriceUtils();
    const { exchangeRates, prices } = storeToRefs(store);
    set(prices, {
      DAI: {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(1),
      },
      ETH: {
        isManualPrice: true,
        oracle: 'manualcurrent',
        value: bigNumberify(2),
      },
    });
    set(exchangeRates, {
      EUR: bigNumberify(1.5),
    });
  });

  describe('useExchangeRate', () => {
    it('should return price when found', () => {
      const exchangeRate = utils.useExchangeRate('EUR');
      expect(get(exchangeRate)).toEqual(bigNumberify(1.5));
    });

    it('should return undefined when price is not found', () => {
      const exchangeRate = utils.useExchangeRate('JPY');
      expect(get(exchangeRate)).toBeUndefined();
    });
  });

  describe('getExchangeRate', () => {
    it('should return rate when found', () => {
      expect(utils.getExchangeRate('EUR')).toEqual(bigNumberify(1.5));
    });

    it('should return undefined when rate is not found', () => {
      expect(utils.getExchangeRate('JPY')).toBeUndefined();
    });

    it('should return the default value when rate is not found', () => {
      expect(utils.getExchangeRate('JPY', bigNumberify(1))).toEqual(bigNumberify(1));
    });
  });

  describe('useAssetPrice', () => {
    it('should return the price if it is found', () => {
      expect(get(utils.useAssetPrice('DAI'))).toEqual(bigNumberify(1));
    });

    it('should return undefined if the price is not found', () => {
      expect(get(utils.useAssetPrice('BTC'))).toBeUndefined();
    });
  });

  describe('getAssetPrice', () => {
    it('should return the price if it is found', () => {
      expect(utils.getAssetPrice('DAI')).toEqual(bigNumberify(1));
    });

    it('should return undefined if the price is not found', () => {
      expect(utils.getAssetPrice('BTC')).toBeUndefined();
    });

    it('should return the default value if the price is not found', () => {
      expect(utils.getAssetPrice('BTC', bigNumberify(0))).toEqual(bigNumberify(0));
    });
  });

  describe('hasCachedPrice', () => {
    it('should return true if the asset has a cached price', () => {
      expect(utils.hasCachedPrice('DAI')).toBe(true);
    });

    it('should return false if the asset has no cached price', () => {
      expect(utils.hasCachedPrice('BTC')).toBe(false);
    });
  });

  describe('useIsManualAssetPrice', () => {
    it('should return false for non-manual price', () => {
      expect(get(utils.useIsManualAssetPrice('DAI'))).toBe(false);
    });

    it('should return true for manual price', () => {
      expect(get(utils.useIsManualAssetPrice('ETH'))).toBe(true);
    });
  });

  describe('isManualAssetPrice', () => {
    it('should return false for non-manual price', () => {
      expect(utils.isManualAssetPrice('DAI')).toBe(false);
    });

    it('should return true for manual price', () => {
      expect(utils.isManualAssetPrice('ETH')).toBe(true);
    });
  });

  describe('getAssetPriceOracle', () => {
    it('should return oracle for known asset', () => {
      expect(utils.getAssetPriceOracle('ETH')).toBe('manualcurrent');
    });

    it('should return empty string for unknown asset', () => {
      expect(utils.getAssetPriceOracle('BTC')).toBe('');
    });
  });
});
