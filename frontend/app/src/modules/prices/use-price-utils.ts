import type { ExchangeRates } from '@/types/user';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { PriceOracle } from '@/types/settings/price-oracle';
import { type BigNumber, One } from '@rotki/common';

interface UsePriceUtilsReturn {
  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  assetPrice: (asset: MaybeRef<string>) => ComputedRef<BigNumber | undefined>;
  useExchangeRate: <T extends BigNumber | undefined = undefined>(
    currency: MaybeRef<string>,
    defaultValue?: T
  ) => ComputedRef<T extends undefined ? BigNumber | undefined : BigNumber>;
  getAssetPriceOracle: (asset: MaybeRef<string>) => ComputedRef<string>;
  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  isAssetPriceInCurrentCurrency: (asset: MaybeRef<string>) => ComputedRef<boolean>;
  isManualAssetPrice: (asset: MaybeRef<string>) => ComputedRef<boolean>;
  toSelectedCurrency: (value: MaybeRef<BigNumber>) => ComputedRef<BigNumber>;
}

export function usePriceUtils(): UsePriceUtilsReturn {
  const { assetPricesWithCurrentCurrency, exchangeRates, prices } = storeToRefs(useBalancePricesStore());
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { assetInfo } = useAssetInfoRetrieval();

  function getExchangeRate(rates: ExchangeRates, currency: string): BigNumber | undefined {
    return rates[currency];
  }

  const useExchangeRate = <T extends BigNumber | undefined>(
    currency: MaybeRef<string>,
    defaultValue?: T,
  ): ComputedRef<T extends undefined ? BigNumber | undefined : BigNumber> => computed(() => {
    const rate = getExchangeRate(get(exchangeRates), get(currency));
    if (rate === undefined)
      return defaultValue as (T extends undefined ? BigNumber | undefined : BigNumber);
    return rate as (T extends undefined ? BigNumber | undefined : BigNumber);
  });

  const toSelectedCurrency = (value: MaybeRef<BigNumber>): ComputedRef<BigNumber> => computed(() => {
    const mainCurrency = get(currencySymbol);
    const currentExchangeRate = get(useExchangeRate(mainCurrency));
    const val = get(value);
    return currentExchangeRate ? val.multipliedBy(currentExchangeRate) : val;
  });

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * This is a hacky way to set EUR => EUR price and EURe => EUR price to 1.
     * @param {MaybeRef<string>} asset
     *
     */
  const isAssetPriceEqualToCurrentCurrency = (asset: MaybeRef<string>): ComputedRef<boolean> => computed(() => {
    const currency = get(currencySymbol);
    return get(asset) === currency || (currency === 'EUR' && get(assetInfo(asset))?.collectionId === '240');
  });

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  const assetPrice = (asset: MaybeRef<string>): ComputedRef<BigNumber | undefined> => computed(() => {
    if (get(isAssetPriceEqualToCurrentCurrency(asset)))
      return One;

    const assetVal = get(asset);

    return get(assetPricesWithCurrentCurrency)[assetVal]?.value ?? get(prices)[assetVal]?.value;
  });

  const getAssetPriceOracle = (asset: MaybeRef<string>): ComputedRef<string> =>
    computed(() => get(prices)[get(asset)]?.oracle || '');

  const isManualAssetPrice = (asset: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => get(getAssetPriceOracle(asset)) === PriceOracle.MANUALCURRENT);

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  const isAssetPriceInCurrentCurrency = (asset: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => (get(isAssetPriceEqualToCurrentCurrency(asset)) || !!get(assetPricesWithCurrentCurrency)[get(asset)]?.value));

  return {
    assetPrice,
    getAssetPriceOracle,
    isAssetPriceInCurrentCurrency,
    isManualAssetPrice,
    toSelectedCurrency,
    useExchangeRate,
  };
}
