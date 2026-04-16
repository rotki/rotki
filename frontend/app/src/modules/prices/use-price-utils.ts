import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface UsePriceUtilsReturn {
  useAssetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<BigNumber | undefined>;
  useExchangeRate: {
    (currency: MaybeRefOrGetter<string>): ComputedRef<BigNumber | undefined>;
    (currency: MaybeRefOrGetter<string>, defaultValue: BigNumber): ComputedRef<BigNumber>;
  };
  useAssetPriceOracle: (asset: MaybeRefOrGetter<string>) => ComputedRef<string>;
  useIsManualAssetPrice: (asset: MaybeRefOrGetter<string>) => ComputedRef<boolean>;
  getAssetPrice: {
    (asset: string): BigNumber | undefined;
    (asset: string, defaultValue: BigNumber): BigNumber;
  };
  getExchangeRate: {
    (currency: string): BigNumber | undefined;
    (currency: string, defaultValue: BigNumber): BigNumber;
  };
  getAssetPriceOracle: (asset: string) => string;
  isManualAssetPrice: (asset: string) => boolean;
  hasCachedPrice: (asset: string) => boolean;
}

export function usePriceUtils(): UsePriceUtilsReturn {
  const {
    exchangeRates,
    prices,
  } = storeToRefs(useBalancePricesStore());

  function useAssetPrice(asset: MaybeRefOrGetter<string>): ComputedRef<BigNumber | undefined> {
    return computed<BigNumber | undefined>(() => get(prices)[toValue(asset)]?.value);
  }

  function getAssetPrice(asset: string): BigNumber | undefined;
  function getAssetPrice(asset: string, defaultValue: BigNumber): BigNumber;

  function getAssetPrice(asset: string, defaultValue?: BigNumber): BigNumber | undefined {
    return get(prices)[asset]?.value ?? defaultValue;
  }

  function useExchangeRate(currency: MaybeRefOrGetter<string>): ComputedRef<BigNumber | undefined>;
  function useExchangeRate(currency: MaybeRefOrGetter<string>, defaultValue: BigNumber): ComputedRef<BigNumber>;

  function useExchangeRate(currency: MaybeRefOrGetter<string>, defaultValue?: BigNumber): ComputedRef<BigNumber | undefined> {
    return computed<BigNumber | undefined>(() => get(exchangeRates)[toValue(currency)] ?? defaultValue);
  }

  function getExchangeRate(currency: string): BigNumber | undefined;
  function getExchangeRate(currency: string, defaultValue: BigNumber): BigNumber;

  function getExchangeRate(currency: string, defaultValue?: BigNumber): BigNumber | undefined {
    return get(exchangeRates)[currency] ?? defaultValue;
  }

  function useAssetPriceOracle(asset: MaybeRefOrGetter<string>): ComputedRef<string> {
    return computed<string>(() => get(prices)[toValue(asset)]?.oracle || '');
  }

  function getAssetPriceOracle(asset: string): string {
    return get(prices)[asset]?.oracle || '';
  }

  function useIsManualAssetPrice(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => get(prices)[toValue(asset)]?.oracle === PriceOracle.MANUALCURRENT);
  }

  function isManualAssetPrice(asset: string): boolean {
    return get(prices)[asset]?.oracle === PriceOracle.MANUALCURRENT;
  }

  function hasCachedPrice(asset: string): boolean {
    return get(prices)[asset]?.value !== undefined;
  }

  return {
    getAssetPrice,
    getAssetPriceOracle,
    getExchangeRate,
    hasCachedPrice,
    isManualAssetPrice,
    useAssetPrice,
    useAssetPriceOracle,
    useExchangeRate,
    useIsManualAssetPrice,
  };
}
