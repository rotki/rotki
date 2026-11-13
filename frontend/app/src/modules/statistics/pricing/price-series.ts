import { type BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';

export interface KnownPrice {
  /** Unix seconds. */
  readonly time: number;
  readonly price: BigNumber;
}

const MISSING: ResolvedPrice = { price: undefined, quality: PriceQuality.MISSING };

/** Whether a quality is a stand-in rather than a price for that time. */
export function isFallbackQuality(quality: PriceQuality): boolean {
  return quality !== PriceQuality.EXACT;
}

/** Index of the first point at or after `time`, or `points.length` when there is none. */
function lowerBound(points: readonly { readonly time: number }[], time: number): number {
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

/** The point of a time-ordered list closest to `time` within `tolerance`, or undefined. */
export function nearestWithin<T extends { readonly time: number }>(points: readonly T[], time: number, tolerance: number): T | undefined {
  const index = lowerBound(points, time);
  const after = points[index];
  const before = index > 0 ? points[index - 1] : undefined;
  const afterDistance = after ? after.time - time : Number.POSITIVE_INFINITY;
  const beforeDistance = before ? time - before.time : Number.POSITIVE_INFINITY;
  const [closest, distance] = beforeDistance <= afterDistance ? [before, beforeDistance] : [after, afterDistance];
  return closest && distance <= tolerance ? closest : undefined;
}

/**
 * Prices each of `times` from known prices, filling gaps by the policy agreed in rotki/rotki#4031.
 *
 * @remarks
 * In order: a known price within a day of the time (the oracles keep one price per day), the
 * nearest earlier price carried forward, the nearest later price for times before the first known
 * one, today's price, and otherwise missing. A gap is never filled with zero: on a chart a run of
 * zeros reads as the holding being lost.
 *
 * @param known - prices in time order, all positive, as the price series store keeps them
 * @param current - today's price, the last resort before missing
 * @param times - the times to price, unix seconds, in any order
 * @returns one resolved price per entry of `times`, in the same order
 */
export function resolvePriceSeries(
  known: readonly KnownPrice[],
  current: BigNumber | undefined,
  times: readonly number[],
): ResolvedPrice[] {
  const today = current?.isFinite() && current.gt(0) ? current : undefined;
  return times.map((time) => {
    const close = nearestWithin(known, time, SECONDS_PER_DAY);
    if (close)
      return { price: close.price, quality: PriceQuality.EXACT, time: close.time };

    const index = lowerBound(known, time);
    if (index > 0)
      return { price: known[index - 1].price, quality: PriceQuality.CARRIED, time: known[index - 1].time };
    if (index < known.length)
      return { price: known[index].price, quality: PriceQuality.BACK_FILLED, time: known[index].time };
    if (today)
      return { price: today, quality: PriceQuality.CURRENT };
    return MISSING;
  });
}
