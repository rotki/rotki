import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useCurrencies } from '@/types/currencies';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeAll, describe, expect, it } from 'vitest';

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
    it('price is found', () => {
      const exchangeRate = utils.useExchangeRate('EUR');
      expect(get(exchangeRate)).toEqual(bigNumberify(1.5));
    });

    it('price is not found ', () => {
      const exchangeRate = utils.useExchangeRate('JPY');
      expect(get(exchangeRate)).toEqual(undefined);
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
      expect(get(utils.assetPrice('BTC'))).toEqual(undefined);
    });
  });

  it('should return if it isManualAssetPrice', () => {
    expect(get(utils.isManualAssetPrice('DAI'))).toEqual(false);
    expect(get(utils.isManualAssetPrice('ETH'))).toEqual(true);
  });

  it('should return if isAssetPriceInCurrentCurrency', () => {
    expect(get(utils.isAssetPriceInCurrentCurrency('DAI'))).toEqual(false);
    expect(get(utils.isAssetPriceInCurrentCurrency('ETH'))).toEqual(false);
  });
});
