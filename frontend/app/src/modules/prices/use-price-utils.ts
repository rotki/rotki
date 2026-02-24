import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ExchangeRates } from '@/types/user';
import { type BigNumber, One } from '@rotki/common';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { PriceOracle } from '@/types/settings/price-oracle';

interface UsePriceUtilsReturn {
  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRefOrGetter<string>} asset
     */
  assetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<BigNumber | undefined>;
  assetPriceInCurrentCurrency: (asset: MaybeRefOrGetter<string>) => ComputedRef<BigNumber>;
  useExchangeRate: <T extends BigNumber | undefined = undefined>(
    currency: MaybeRefOrGetter<string>,
    defaultValue?: T
  ) => ComputedRef<T extends undefined ? BigNumber | undefined : BigNumber>;
  getAssetPriceOracle: (asset: MaybeRefOrGetter<string>) => ComputedRef<string>;
  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRefOrGetter<string>} asset
     */
  isAssetPriceInCurrentCurrency: (asset: MaybeRefOrGetter<string>) => ComputedRef<boolean>;
  isManualAssetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<boolean>;
  toSelectedCurrency: (value: MaybeRefOrGetter<BigNumber>) => ComputedRef<BigNumber>;
  hasCachedPrice: (asset: string) => boolean;
  getAssetPrice: <T extends BigNumber | undefined = undefined>(
    asset: string,
    defaultValue?: T
  ) => T extends undefined ? BigNumber | undefined : BigNumber;
}

export function usePriceUtils(): UsePriceUtilsReturn {
  const {
    assetPricesWithCurrentCurrency,
    euroCollectionAssets,
    exchangeRates,
    prices,
  } = storeToRefs(useBalancePricesStore());
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  function getExchangeRate(rates: ExchangeRates, currency: string): BigNumber | undefined {
    return rates[currency];
  }

  const useExchangeRate = <T extends BigNumber | undefined>(
    currency: MaybeRefOrGetter<string>,
    defaultValue?: T,
  ): ComputedRef<T extends undefined ? BigNumber | undefined : BigNumber> => computed(() => {
    const rate = getExchangeRate(get(exchangeRates), toValue(currency));
    if (rate === undefined)
      return defaultValue as (T extends undefined ? BigNumber | undefined : BigNumber);
    return rate as (T extends undefined ? BigNumber | undefined : BigNumber);
  });

  const toSelectedCurrency = (value: MaybeRefOrGetter<BigNumber>): ComputedRef<BigNumber> => computed(() => {
    const mainCurrency = get(currencySymbol);
    const currentExchangeRate = get(useExchangeRate(mainCurrency));
    const val = toValue(value);
    return currentExchangeRate ? val.multipliedBy(currentExchangeRate) : val;
  });

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * This is a hacky way to set EUR => EUR price and EURe => EUR price to 1.
     * @param {MaybeRef<string>} asset
     *
     */
  const isAssetPriceEqualToCurrentCurrency = (asset: MaybeRefOrGetter<string>): ComputedRef<boolean> => computed(() => {
    const currency = get(currencySymbol);
    const assetIdentifier = toValue(asset);
    return assetIdentifier === currency || (currency === 'EUR' && get(euroCollectionAssets).includes(assetIdentifier));
  });

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  const assetPrice = (asset: MaybeRefOrGetter<string>): ComputedRef<BigNumber | undefined> => computed(() => {
    if (get(isAssetPriceEqualToCurrentCurrency(asset)))
      return One;

    const assetVal = toValue(asset);

    return get(assetPricesWithCurrentCurrency)[assetVal]?.value ?? get(prices)[assetVal]?.value;
  });

  /**
   * @deprecated
   * TODO: Remove this immediately.
   * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
   * @param {MaybeRef<string>} asset
   */
  const assetPriceInCurrentCurrency = (asset: MaybeRefOrGetter<string>): ComputedRef<BigNumber> => computed(() => {
    const price = get(assetPrice(asset)) || One;

    if (get(isAssetPriceInCurrentCurrency(asset))) {
      return price;
    }

    return get(toSelectedCurrency(price));
  });

  const getAssetPriceOracle = (asset: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed(() => get(prices)[toValue(asset)]?.oracle || '');

  const isManualAssetPrice = (asset: MaybeRefOrGetter<string>): ComputedRef<boolean> =>
    computed(() => get(getAssetPriceOracle(asset)) === PriceOracle.MANUALCURRENT);

  /**
     * @deprecated
     * TODO: Remove this immediately.
     * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
     * @param {MaybeRef<string>} asset
     */
  function isAssetPriceInCurrentCurrency(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed(() => (get(isAssetPriceEqualToCurrentCurrency(asset)) || !!get(assetPricesWithCurrentCurrency)[toValue(asset)]?.value));
  }

  function hasCachedPrice(asset: string): boolean {
    return (get(assetPricesWithCurrentCurrency)[asset]?.value ?? get(prices)[asset]?.value) !== undefined;
  }

  function getAssetPrice<T extends BigNumber | undefined = undefined>(
    asset: string,
    defaultValue?: T,
  ): T extends undefined ? BigNumber | undefined : BigNumber {
    const currency = get(currencySymbol);
    const isEqualToCurrentCurrency = asset === currency || (currency === 'EUR' && get(euroCollectionAssets).includes(asset));

    if (isEqualToCurrentCurrency) {
      return One as (T extends undefined ? BigNumber | undefined : BigNumber);
    }

    const price = get(assetPricesWithCurrentCurrency)[asset]?.value ?? get(prices)[asset]?.value;

    if (price === undefined) {
      return defaultValue as (T extends undefined ? BigNumber | undefined : BigNumber);
    }

    return price as (T extends undefined ? BigNumber | undefined : BigNumber);
  }

  return {
    assetPrice,
    assetPriceInCurrentCurrency,
    getAssetPrice,
    getAssetPriceOracle,
    hasCachedPrice,
    isAssetPriceInCurrentCurrency,
    isManualAssetPrice,
    toSelectedCurrency,
    useExchangeRate,
  };
}
