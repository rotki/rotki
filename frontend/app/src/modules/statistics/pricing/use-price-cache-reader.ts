import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { EXACT_TOLERANCE_SECONDS, type KnownPrice } from '@/modules/statistics/pricing/price-series';
import { PricePair, usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** Asset and time pairs per cache request, so one chart never sends one huge payload. */
const CACHE_READ_CHUNK = 1000;

interface CacheQuery {
  readonly pair: PricePair;
  readonly target: string;
  readonly assets: readonly string[];
}

interface UsePriceCacheReaderReturn {
  /** Reads every not yet requested price of `assets` at `times` from the backend cache. */
  readCached: (assets: readonly string[], times: readonly number[]) => Promise<void>;
}

function requestKey(pair: PricePair, asset: string, time: number): string {
  return `${pair}:${asset}:${time}`;
}

function chunk<T>(items: readonly T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size)
    chunks.push(items.slice(index, index + size));
  return chunks;
}

/**
 * The cache reads a price series needs: each asset in the main currency, and, outside USD, each
 * asset in USD plus the USD rate itself, so a USD price cached before a currency switch still
 * prices the series through the rate.
 */
function queriesFor(assets: readonly string[], currency: string): CacheQuery[] {
  const priced = assets.filter(asset => asset !== currency);
  if (currency === CURRENCY_USD)
    return [{ assets: priced, pair: PricePair.MAIN, target: currency }];
  return [
    { assets: [...new Set([...priced, CURRENCY_USD])], pair: PricePair.MAIN, target: currency },
    { assets: priced.filter(asset => asset !== CURRENCY_USD), pair: PricePair.USD, target: CURRENCY_USD },
  ];
}

/**
 * Reads historic prices from the backend's price cache only, never from an oracle.
 *
 * @remarks
 * Nothing leaves the machine, so this runs on every render. A miss is left for the resolver to fill
 * and for the backfill to fetch.
 */
export function usePriceCacheReader(): UsePriceCacheReaderReturn {
  const store = usePriceSeriesStore();
  const { requested } = storeToRefs(store);
  const currencySymbol = useSetting('currencySymbol');
  const { queryOnlyCacheHistoricalRates } = usePriceApi();

  async function readChunk(query: CacheQuery, pairs: readonly [string, number][]): Promise<void> {
    const keys = pairs.map(([asset, time]) => requestKey(query.pair, asset, time));
    store.markRequested(keys);
    try {
      const result = await queryOnlyCacheHistoricalRates({
        assetsTimestamp: pairs.map(([asset, time]) => [asset, time.toString()]),
        onlyCachePeriod: EXACT_TOLERANCE_SECONDS,
        targetAsset: query.target,
      });
      for (const [asset, prices] of Object.entries(result.assets)) {
        const points: KnownPrice[] = Object.entries(prices)
          .filter(([, price]) => price.gt(0))
          .map(([time, price]) => ({ price, time: Number(time) }));
        store.addPrices(query.pair, asset, points);
      }
    }
    catch (error: unknown) {
      logger.error(error);
      store.forgetRequested(keys);
    }
  }

  async function readCached(assets: readonly string[], times: readonly number[]): Promise<void> {
    const seen = get(requested);
    for (const query of queriesFor(assets, get(currencySymbol))) {
      const pairs = query.assets
        .flatMap(asset => times.map((time): [string, number] => [asset, time]))
        .filter(([asset, time]) => !seen.has(requestKey(query.pair, asset, time)));
      for (const part of chunk(pairs, CACHE_READ_CHUNK))
        await readChunk(query, part);
    }
  }

  return { readCached };
}
