import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, One, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { resolvePriceSeries } from '@/modules/statistics/pricing/price-series';
import { usePriceCacheReader } from '@/modules/statistics/pricing/use-price-cache-reader';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** How long the requested assets and times must settle before the cache is read. */
const READ_DEBOUNCE_MS = 300;

interface UsePriceSeriesReturn {
  /** Per asset, one resolved price in the main currency per requested time. */
  readonly series: ComputedRef<ReadonlyMap<string, readonly ResolvedPrice[]>>;
}

/**
 * Historic prices of `assets` at each of `times`, in the main currency, with gaps filled.
 *
 * @remarks
 * The single way the graphs price a series: the dashboard net value (both views) and, through the
 * premium API, the asset value graph. Reads only the backend cache; what is missing stays a
 * flagged stand-in until `usePriceBackfill` fetches it. The main currency itself is always one,
 * and USD is priced by the USD rate. Everything is dropped when the main currency changes.
 *
 * @param assets - asset identifiers
 * @param times - unix seconds
 */
export function usePriceSeries(
  assets: MaybeRefOrGetter<readonly string[]>,
  times: MaybeRefOrGetter<readonly number[]>,
): UsePriceSeriesReturn {
  const { mainPrices, usdPrices } = storeToRefs(usePriceSeriesStore());
  const currencySymbol = useSetting('currencySymbol');
  const { getAssetPrice, getExchangeRate } = usePriceUtils();
  const { readCached } = usePriceCacheReader();

  function currentPrice(asset: string, currency: string): BigNumber | undefined {
    return asset === CURRENCY_USD ? getExchangeRate(currency) : getAssetPrice(asset);
  }

  function resolveAsset(asset: string, requestedTimes: readonly number[]): ResolvedPrice[] {
    const currency = get(currencySymbol);
    if (asset === currency)
      return requestedTimes.map(() => ({ price: One, quality: PriceQuality.EXACT }));
    const usdToMain = currency === CURRENCY_USD ? undefined : get(mainPrices)[CURRENCY_USD];
    return resolvePriceSeries({
      current: currentPrice(asset, currency),
      direct: get(mainPrices)[asset] ?? [],
      usdToMain,
      viaUsd: get(usdPrices)[asset],
    }, requestedTimes);
  }

  const series = computed<ReadonlyMap<string, readonly ResolvedPrice[]>>(() => {
    const requestedTimes = toValue(times);
    return new Map(toValue(assets).map(asset => [asset, resolveAsset(asset, requestedTimes)]));
  });

  watchDebounced(
    [(): readonly string[] => toValue(assets), (): readonly number[] => toValue(times), currencySymbol],
    ([nextAssets, nextTimes]) => startPromise(readCached(nextAssets, nextTimes)),
    { debounce: READ_DEBOUNCE_MS, immediate: true },
  );

  return { series };
}
