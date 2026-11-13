import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
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

  /** Reads one chunk; a failed read is logged and let go, so the times can be asked again. */
  async function readChunk(asset: string, currency: string, times: readonly number[]): Promise<KnownPrice[]> {
    const keys = times.map(time => requestKey(asset, time));
    store.markRequested(keys);
    return pipe(
      fromPromise(queryOnlyCacheHistoricalRates({
        assetsTimestamp: times.map(time => [asset, time.toString()]),
        onlyCachePeriod: SECONDS_PER_DAY,
        targetAsset: currency,
      }), (error: unknown) => error),
      map(result => Object.entries(result.assets[asset] ?? {}).map(([time, price]): KnownPrice => ({ price, time: Number(time) }))),
      tapError((error) => {
        logger.error(error);
        store.forgetRequested(keys);
      }),
      getOr<KnownPrice[]>([]),
    );
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
