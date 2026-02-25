import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ExchangeRates } from '@/types/user';
import { useBalancePricesStore } from '@/store/balances/prices';
import { PriceOracle } from '@/types/settings/price-oracle';

interface UsePriceUtilsReturn {
  assetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<BigNumber | undefined>;
  useExchangeRate: <T extends BigNumber | undefined = undefined>(
    currency: MaybeRefOrGetter<string>,
    defaultValue?: T,
  ) => ComputedRef<T extends undefined ? BigNumber | undefined : BigNumber>;
  getAssetPriceOracle: (asset: MaybeRefOrGetter<string>) => ComputedRef<string>;
  isManualAssetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<boolean>;
  hasCachedPrice: (asset: string) => boolean;
  getAssetPrice: <T extends BigNumber | undefined = undefined>(
    asset: string,
    defaultValue?: T,
  ) => T extends undefined ? BigNumber | undefined : BigNumber;
}

export function usePriceUtils(): UsePriceUtilsReturn {
  const {
    exchangeRates,
    prices,
  } = storeToRefs(useBalancePricesStore());

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

  const assetPrice = (asset: MaybeRefOrGetter<string>): ComputedRef<BigNumber | undefined> => computed(() => {
    const assetVal = toValue(asset);
    return get(prices)[assetVal]?.value;
  });

  const getAssetPriceOracle = (asset: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed(() => get(prices)[toValue(asset)]?.oracle || '');

  const isManualAssetPrice = (asset: MaybeRefOrGetter<string>): ComputedRef<boolean> =>
    computed(() => get(getAssetPriceOracle(asset)) === PriceOracle.MANUALCURRENT);

  function hasCachedPrice(asset: string): boolean {
    return get(prices)[asset]?.value !== undefined;
  }

  function getAssetPrice<T extends BigNumber | undefined = undefined>(
    asset: string,
    defaultValue?: T,
  ): T extends undefined ? BigNumber | undefined : BigNumber {
    const price = get(prices)[asset]?.value;

    if (price === undefined) {
      return defaultValue as (T extends undefined ? BigNumber | undefined : BigNumber);
    }

    return price as (T extends undefined ? BigNumber | undefined : BigNumber);
  }

  return {
    assetPrice,
    getAssetPrice,
    getAssetPriceOracle,
    hasCachedPrice,
    isManualAssetPrice,
    useExchangeRate,
  };
}
