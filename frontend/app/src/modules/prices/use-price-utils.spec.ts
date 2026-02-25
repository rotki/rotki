import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeAll, describe, expect, it } from 'vitest';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useCurrencies } from '@/types/currencies';

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

  it('should convert the price toSelectedCurrency', () => {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('EUR') });

    const convertedValue = utils.toSelectedCurrency(bigNumberify(10));

    expect(get(convertedValue)).toEqual(bigNumberify(15));
  });

  describe('assetPrice', () => {
    it('should return the price if it is found', () => {
      expect(get(utils.assetPrice('DAI'))).toEqual(bigNumberify(1));
    });

    it('should return undefined if the price is not found', () => {
      expect(get(utils.assetPrice('BTC'))).toBeUndefined();
    });
  });

  it('should return if it isManualAssetPrice', () => {
    expect(get(utils.isManualAssetPrice('DAI'))).toBe(false);
    expect(get(utils.isManualAssetPrice('ETH'))).toBe(true);
  });

  it('should return if isAssetPriceInCurrentCurrency', () => {
    expect(get(utils.isAssetPriceInCurrentCurrency('DAI'))).toBe(false);
    expect(get(utils.isAssetPriceInCurrentCurrency('ETH'))).toBe(false);
  });
});
