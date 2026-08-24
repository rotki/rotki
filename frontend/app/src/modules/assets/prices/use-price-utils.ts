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
  isPricePending: (asset: string) => boolean;
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

  /**
   * Whether the asset's price has not arrived yet, as opposed to being known.
   *
   * This is the question every value cell has to ask, because a value is only trustworthy once a
   * price exists: with one, a balance is valued as `amount × price` over the whole holding
   * (`price-utils.ts`); without one it falls back to the values the backend attached to whichever
   * chains have reported so far, which is a fraction of the amount shown beside it.
   *
   * A price reads zero-ish in three different situations and only one of them is an answer:
   * absent or negative means nothing has been fetched; a plain zero means a refresh is coming,
   * since `usePriceRefresh` queues exactly the assets with no cached price; a zero carrying
   * `priceMissing` means every oracle was asked and none could price it, which is knowledge and
   * renders as "unknown" rather than as a wait.
   */
  function isPricePending(asset: string): boolean {
    const price = get(prices)[asset];
    if (!price)
      return true;

    if (price.value.isNegative())
      return true;

    return price.value.isZero() && price.priceMissing !== true;
  }

  return {
    getAssetPrice,
    getAssetPriceOracle,
    getExchangeRate,
    hasCachedPrice,
    isManualAssetPrice,
    isPricePending,
    useAssetPrice,
    useAssetPriceOracle,
    useExchangeRate,
    useIsManualAssetPrice,
  };
}
