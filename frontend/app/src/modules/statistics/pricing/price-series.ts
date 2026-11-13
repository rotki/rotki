import { type BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';

/** Seconds in a day. */
export const DAY_SECONDS = 86_400;

/** How far a cached price may sit from the requested time and still count as that time's price. */
export const EXACT_TOLERANCE_SECONDS = DAY_SECONDS / 2;

export interface KnownPrice {
  /** Unix seconds. */
  readonly time: number;
  readonly price: BigNumber;
}

export interface PriceSources {
  /** Cached prices of the asset in the main currency. */
  readonly direct: readonly KnownPrice[];
  /** Cached prices of the asset in USD, combined with `usdToMain` when the direct pair misses. */
  readonly viaUsd?: readonly KnownPrice[];
  /** Cached USD to main currency rates. */
  readonly usdToMain?: readonly KnownPrice[];
  /** Today's price in the main currency, the last resort before missing. */
  readonly current?: BigNumber;
}

export interface EffectivePrice extends KnownPrice {
  readonly derived: boolean;
}

const MISSING: ResolvedPrice = { price: undefined, quality: PriceQuality.MISSING };

/** Whether a quality is a stand-in rather than a price for that time. */
export function isFallbackQuality(quality: PriceQuality): boolean {
  return quality !== PriceQuality.EXACT && quality !== PriceQuality.DERIVED;
}

function byTime(a: KnownPrice, b: KnownPrice): number {
  return a.time - b.time;
}

function usable(points: readonly KnownPrice[] | undefined): KnownPrice[] {
  return (points ?? []).filter(point => point.price.isFinite() && point.price.gt(0)).sort(byTime);
}

/** Index of the first point at or after `time`, or `points.length` when there is none. */
function lowerBound(points: readonly KnownPrice[], time: number): number {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (points[mid].time < time)
      low = mid + 1;
    else
      high = mid;
  }
  return low;
}

/** The point closest to `time` within `tolerance`, or undefined. */
export function nearestWithin<T extends KnownPrice>(points: readonly T[], time: number, tolerance: number): T | undefined {
  const index = lowerBound(points, time);
  const after = points[index];
  const before = index > 0 ? points[index - 1] : undefined;
  const afterDistance = after ? after.time - time : Number.POSITIVE_INFINITY;
  const beforeDistance = before ? time - before.time : Number.POSITIVE_INFINITY;
  const [closest, distance] = beforeDistance <= afterDistance ? [before, beforeDistance] : [after, afterDistance];
  return closest && distance <= tolerance ? closest : undefined;
}

/**
 * Every price the cache can stand behind: direct prices, plus USD prices converted at a USD rate
 * from the same time where no direct price is close.
 */
export function knownPrices(sources: PriceSources, tolerance: number = EXACT_TOLERANCE_SECONDS): EffectivePrice[] {
  const direct = usable(sources.direct);
  const usdRates = usable(sources.usdToMain);
  const derived: EffectivePrice[] = [];
  for (const point of usable(sources.viaUsd)) {
    if (nearestWithin(direct, point.time, tolerance))
      continue;
    const rate = nearestWithin(usdRates, point.time, tolerance);
    if (rate)
      derived.push({ derived: true, price: point.price.multipliedBy(rate.price), time: point.time });
  }
  return [...direct.map(point => ({ ...point, derived: false })), ...derived].sort(byTime);
}

/**
 * Prices an asset at each of `times`, filling gaps by the policy agreed in rotki/rotki#4031.
 *
 * @remarks
 * In order: a cached price close to the time (exact, or derived through USD), the nearest earlier
 * price carried forward, the nearest later price for times before the first known one, today's
 * price, and otherwise missing. A gap is never filled with zero: on a chart a run of zeros reads as
 * the holding being lost.
 *
 * @param sources - cached prices around the range and today's price
 * @param times - the times to price, unix seconds, in any order
 * @param tolerance - how close a cached price must be to count as exact, in seconds
 * @returns one resolved price per entry of `times`, in the same order
 */
export function resolvePriceSeries(
  sources: PriceSources,
  times: readonly number[],
  tolerance: number = EXACT_TOLERANCE_SECONDS,
): ResolvedPrice[] {
  const known = knownPrices(sources, tolerance);
  const current = sources.current?.isFinite() && sources.current.gt(0) ? sources.current : undefined;

  return times.map((time) => {
    const close = nearestWithin(known, time, tolerance);
    if (close)
      return { price: close.price, quality: close.derived ? PriceQuality.DERIVED : PriceQuality.EXACT };

    const index = lowerBound(known, time);
    if (index > 0)
      return { price: known[index - 1].price, quality: PriceQuality.CARRIED };
    if (index < known.length)
      return { price: known[index].price, quality: PriceQuality.BACK_FILLED };
    if (current)
      return { price: current, quality: PriceQuality.CURRENT };
    return MISSING;
  });
}
