import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { One, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { resolvePriceSeries } from '@/modules/statistics/pricing/price-series';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceCacheReader } from '@/modules/statistics/pricing/use-price-cache-reader';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** How long the requested times must settle before the cache is read. */
const READ_DEBOUNCE_MS = 300;

interface UseUsdRatesReturn {
  /** One USD to main currency rate per requested time, gaps filled and flagged. */
  readonly rates: ComputedRef<readonly ResolvedPrice[]>;
  /** Reads the cache again for every time, for after a rate was added by hand. */
  readonly reload: () => Promise<void>;
}

/**
 * The USD to main currency rate at each of `times`, for converting values stored in USD
 * (rotki/rotki#4031).
 *
 * @remarks
 * Reads the backend cache and registers a backfill demand under `id` for the rates still missing,
 * which the oracles are asked for in the background: a currency rate tells them the main currency
 * and nothing about holdings. In USD every rate is one and nothing is read or fetched.
 *
 * @param id - the backfill demand id, unique per caller
 * @param times - unix seconds
 */
export function useUsdRates(id: string, times: MaybeRefOrGetter<readonly number[]>): UseUsdRatesReturn {
  const { prices } = storeToRefs(usePriceSeriesStore());
  const currencySymbol = useSetting('currencySymbol');
  const { getExchangeRate } = usePriceUtils();
  const { readCached } = usePriceCacheReader();

  const isUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

  const rates = computed<readonly ResolvedPrice[]>(() => {
    const requested = toValue(times);
    if (get(isUsd))
      return requested.map(() => ({ price: One, quality: PriceQuality.EXACT }));
    return resolvePriceSeries(get(prices)[CURRENCY_USD] ?? [], getExchangeRate(get(currencySymbol)), requested);
  });

  watchDebounced(
    [(): readonly number[] => toValue(times), isUsd],
    ([requested, usd]) => {
      if (!usd && requested.length > 0)
        startPromise(readCached(CURRENCY_USD, requested));
    },
    { debounce: READ_DEBOUNCE_MS, immediate: true },
  );

  usePriceBackfill().register(id, computed<BackfillDemand | undefined>(() => {
    const requested = toValue(times);
    return get(isUsd) || requested.length === 0 ? undefined : { asset: CURRENCY_USD, times: requested };
  }));

  async function reload(): Promise<void> {
    if (!get(isUsd))
      await readCached(CURRENCY_USD, toValue(times), true);
  }

  return { rates, reload };
}
