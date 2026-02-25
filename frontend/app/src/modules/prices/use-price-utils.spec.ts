import { bigNumberify } from '@rotki/common';
import { beforeAll, describe, expect, it } from 'vitest';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useBalancePricesStore } from '@/store/balances/prices';

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

  describe('exchangeRate', () => {
    it('should return price when found', () => {
      const exchangeRate = utils.useExchangeRate('EUR');
      expect(get(exchangeRate)).toEqual(bigNumberify(1.5));
    });

    it('should return undefined when price is not found', () => {
      const exchangeRate = utils.useExchangeRate('JPY');
      expect(get(exchangeRate)).toBeUndefined();
    });
  });

  describe('assetPrice', () => {
    it('should return the price if it is found', () => {
      expect(get(utils.assetPrice('DAI'))).toEqual(bigNumberify(1));
    });

    it('should return undefined if the price is not found', () => {
      expect(get(utils.assetPrice('BTC'))).toBeUndefined();
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

  it('should return if it isManualAssetPrice', () => {
    expect(get(utils.isManualAssetPrice('DAI'))).toBe(false);
    expect(get(utils.isManualAssetPrice('ETH'))).toBe(true);
  });
});
