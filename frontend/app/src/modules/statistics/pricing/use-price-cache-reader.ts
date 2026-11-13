import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
import { One } from '@rotki/common';
import { chunk } from 'es-toolkit';
import { pipe } from 'plainfp';
import { fromPromise, getOr, map, tapError } from 'plainfp/result-async';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** Times per cache request, so one chart never sends one huge payload. */
const CACHE_READ_CHUNK = 1000;

interface UsePriceCacheReaderReturn {
  /**
   * Reads every not yet requested price of `asset` at `times` from the backend cache, in the main
   * currency.
   *
   * @remarks
   * `force` reads again what was already requested, for after a price was added by hand.
   */
  readCached: (asset: string, times: readonly number[], force?: boolean) => Promise<void>;
}

function requestKey(asset: string, time: number): string {
  return `${asset}:${time}`;
}

/**
 * Reads historic prices from the backend's price cache only, never from an oracle.
 *
 * @remarks
 * Nothing leaves the machine, so this runs on every render. A miss is left for the resolver to fill
 * and for the backfill to fetch. A read that answers after the main currency changed is dropped:
 * the store was emptied for the new currency, and the series asks again in it.
 */
export function usePriceCacheReader(): UsePriceCacheReaderReturn {
  const store = usePriceSeriesStore();
  const currencySymbol = useSetting('currencySymbol');
  const { queryOnlyCacheHistoricalRates } = usePriceApi();

  /** One cache read of `from` priced in `to`, positive prices only; undefined when the read failed. */
  async function query(from: string, to: string, times: readonly number[]): Promise<KnownPrice[] | undefined> {
    return pipe(
      fromPromise(queryOnlyCacheHistoricalRates({
        assetsTimestamp: times.map(time => [from, time.toString()]),
        onlyCachePeriod: SECONDS_PER_DAY,
        targetAsset: to,
      }), (error: unknown) => error),
      map(result => Object.entries(result.assets[from] ?? {})
        .map(([time, price]): KnownPrice => ({ price, time: Number(time) }))
        .filter(point => point.price.gt(0))),
      tapError(error => logger.error(error)),
      getOr<KnownPrice[] | undefined>(undefined),
    );
  }

  /**
   * Reads one chunk: `asset` priced in `currency`, and for the times that misses, `currency` priced
   * in `asset`, inverted.
   *
   * @remarks
   * The backend prices a fiat in a crypto by inverting the crypto's fiat price and does not store
   * the inverse, so with a crypto main currency only the second read finds the rates it fetched. A
   * failed read lets its times be asked again.
   */
  async function readChunk(asset: string, currency: string, times: readonly number[]): Promise<KnownPrice[]> {
    store.markRequested(times.map(time => requestKey(asset, time)));
    const direct = await query(asset, currency, times);
    if (!direct) {
      store.forgetRequested(times.map(time => requestKey(asset, time)));
      return [];
    }
    const found = new Set(direct.map(point => point.time));
    const missing = times.filter(time => !found.has(time));
    if (missing.length === 0)
      return direct;
    const inverse = await query(currency, asset, missing);
    if (!inverse)
      store.forgetRequested(missing.map(time => requestKey(asset, time)));
    return [...direct, ...(inverse ?? []).map(point => ({ price: One.dividedBy(point.price), time: point.time }))];
  }

  async function readCached(asset: string, times: readonly number[], force = false): Promise<void> {
    const currency = get(currencySymbol);
    const pending = force ? [...times] : times.filter(time => !store.isRequested(requestKey(asset, time)));
    const points: KnownPrice[] = [];
    for (const part of chunk(pending, CACHE_READ_CHUNK))
      points.push(...await readChunk(asset, currency, part));
    if (get(currencySymbol) === currency)
      store.addPrices(asset, points);
  }

  return { readCached };
}
