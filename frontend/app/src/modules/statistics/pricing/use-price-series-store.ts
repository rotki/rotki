import type { ShallowRef } from 'vue';
import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useSetting } from '@/modules/settings/use-setting';

/** Which cached pair a set of prices belongs to. */
export const PricePair = {
  /** The asset in the main currency. */
  MAIN: 'main',
  /** The asset in USD, combined with the USD rate when the main pair misses. */
  USD: 'usd',
} as const;

export type PricePair = typeof PricePair[keyof typeof PricePair];

type PricesByAsset = Readonly<Record<string, readonly KnownPrice[]>>;

function merge(existing: readonly KnownPrice[] | undefined, added: readonly KnownPrice[]): KnownPrice[] {
  const byTime = new Map<number, KnownPrice>((existing ?? []).map(point => [point.time, point]));
  for (const point of added)
    byTime.set(point.time, point);
  return [...byTime.values()].sort((a, b) => a.time - b.time);
}

/**
 * The historic prices the price series have read from the backend cache or fetched, per pair.
 *
 * @remarks
 * State only: `usePriceSeries` reads the cache into it and `usePriceBackfill` adds what it
 * fetches. Prices are in the main currency (or USD for the USD pair), so the whole store is
 * dropped when the main currency changes. `requested` remembers which asset and time pairs were
 * already asked of the cache, so re-rendering a chart does not ask again.
 */
export const usePriceSeriesStore = defineStore('statistics/price-series', () => {
  const mainPrices = shallowRef<PricesByAsset>({});
  const usdPrices = shallowRef<PricesByAsset>({});
  const requested = shallowRef<ReadonlySet<string>>(new Set());

  function pricesOf(pair: PricePair): ShallowRef<PricesByAsset> {
    return pair === PricePair.MAIN ? mainPrices : usdPrices;
  }

  function addPrices(pair: PricePair, asset: string, points: readonly KnownPrice[]): void {
    if (points.length === 0)
      return;
    const target = pricesOf(pair);
    const current = get(target);
    set(target, { ...current, [asset]: merge(current[asset], points) });
  }

  function markRequested(keys: readonly string[]): void {
    if (keys.length === 0)
      return;
    set(requested, new Set([...get(requested), ...keys]));
  }

  /** Lets a failed read be asked again. */
  function forgetRequested(keys: readonly string[]): void {
    const remaining = new Set(get(requested));
    for (const key of keys)
      remaining.delete(key);
    set(requested, remaining);
  }

  function reset(): void {
    set(mainPrices, {});
    set(usdPrices, {});
    set(requested, new Set());
  }

  watch(useSetting('currencySymbol'), reset);
  onSessionCleared('price-series', reset);

  return {
    addPrices,
    forgetRequested,
    mainPrices,
    markRequested,
    requested,
    reset,
    usdPrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePriceSeriesStore, import.meta.hot));
