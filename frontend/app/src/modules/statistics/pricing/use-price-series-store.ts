import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useSetting } from '@/modules/settings/use-setting';

type PricesByAsset = Readonly<Record<string, readonly KnownPrice[]>>;

/** Merges two time-ordered lists in one pass; on a shared time the added point wins. */
function merge(existing: readonly KnownPrice[], added: readonly KnownPrice[]): KnownPrice[] {
  const merged: KnownPrice[] = [];
  let left = 0;
  let right = 0;
  while (left < existing.length || right < added.length) {
    const fromExisting = existing[left];
    const fromAdded = added[right];
    if (!fromAdded || (fromExisting && fromExisting.time < fromAdded.time)) {
      merged.push(fromExisting);
      left += 1;
      continue;
    }
    if (fromExisting?.time === fromAdded.time)
      left += 1;
    merged.push(fromAdded);
    right += 1;
  }
  return merged;
}

/**
 * The historic prices in the main currency that the graphs have read from the backend cache or
 * fetched, per asset.
 *
 * @remarks
 * State only: `useUsdRates` reads the cache into it and `usePriceBackfill` adds what it fetches.
 * Each asset's list is kept in time order with positive prices only, which is what the resolver
 * expects. Prices are in the main currency, so the whole store is dropped when it changes.
 * `requested` remembers which asset and time pairs were already asked of the cache, so re-rendering
 * a chart does not ask again; nothing renders from it, so it is a plain set.
 */
export const usePriceSeriesStore = defineStore('statistics/price-series', () => {
  const prices = shallowRef<PricesByAsset>({});
  const requested = new Set<string>();

  function addPrices(asset: string, points: readonly KnownPrice[]): void {
    const added = points.filter(point => point.price.isFinite() && point.price.gt(0)).sort((a, b) => a.time - b.time);
    if (added.length === 0)
      return;
    const current = get(prices);
    set(prices, { ...current, [asset]: merge(current[asset] ?? [], added) });
  }

  function isRequested(key: string): boolean {
    return requested.has(key);
  }

  function markRequested(keys: readonly string[]): void {
    for (const key of keys)
      requested.add(key);
  }

  /** Lets a failed read be asked again. */
  function forgetRequested(keys: readonly string[]): void {
    for (const key of keys)
      requested.delete(key);
  }

  function reset(): void {
    set(prices, {});
    requested.clear();
  }

  watch(useSetting('currencySymbol'), reset);
  onSessionCleared('price-series', reset);

  return {
    addPrices,
    forgetRequested,
    isRequested,
    markRequested,
    prices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePriceSeriesStore, import.meta.hot));
