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

  /**
   * A price reads zero-ish in three situations and only one of them is an answer. Value cells key
   * their loading state off this, so conflating them either prints a zero for an unpriced holding
   * or leaves an unpriceable one loading forever.
   */
  describe('isPricePending', () => {
    beforeAll(() => {
      const { prices } = storeToRefs(store);
      set(prices, {
        ...get(prices),
        NEGATIVE: { isManualPrice: false, oracle: '', value: bigNumberify(-1) },
        SEEDED: { isManualPrice: false, oracle: '', value: bigNumberify(5) },
        ZERO_MISSING: { isManualPrice: false, oracle: 'blockchain', priceMissing: true, value: bigNumberify(0) },
        ZERO_QUEUED: { isManualPrice: false, oracle: 'coingecko', value: bigNumberify(0) },
      });
    });

    it('should be pending for an asset that has never been fetched', () => {
      expect(utils.isPricePending('BTC')).toBe(true);
    });

    it('should be pending for the negative no-price sentinel', () => {
      expect(utils.isPricePending('NEGATIVE')).toBe(true);
    });

    it('should be pending for a plain zero, which is a queued refresh', () => {
      expect(utils.isPricePending('ZERO_QUEUED')).toBe(true);
    });

    it('should not be pending for a zero no oracle could price', () => {
      expect(utils.isPricePending('ZERO_MISSING')).toBe(false);
    });

    it('should not be pending for a seeded price', () => {
      expect(utils.isPricePending('SEEDED')).toBe(false);
    });

    it('should not be pending for a live price', () => {
      expect(utils.isPricePending('DAI')).toBe(false);
    });
  });
});
