import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { type BackfillAsset, type BackfillRequest, DAYS_PER_REQUEST, dayStart, planBackfill } from '@/modules/statistics/pricing/backfill-plan';

const NOON = SECONDS_PER_DAY / 2;

function at(day: number): number {
  return day * SECONDS_PER_DAY + NOON;
}

function price(day: number): KnownPrice {
  return { price: bigNumberify(1), time: day * SECONDS_PER_DAY };
}

function usd(times: number[], known: KnownPrice[] = [], failed: number[] = []): BackfillAsset {
  return { asset: 'USD', failed: new Set(failed), known, times };
}

/** The days a request asks for, as day numbers. */
function requestedDays(request: BackfillRequest | undefined): number[] {
  if (!request)
    return [];
  const excluded = new Set(request.excludeTimestamps);
  const days: number[] = [];
  for (let time = request.fromTimestamp; time <= request.toTimestamp; time += SECONDS_PER_DAY) {
    if (!excluded.has(time))
      days.push(time / SECONDS_PER_DAY);
  }
  return days;
}

function range(from: number, to: number): number[] {
  return Array.from({ length: to - from + 1 }, (_, index) => from + index);
}

describe('modules/statistics/pricing/backfill-plan', () => {
  it('should ask for one day a month first across the whole history', () => {
    const [request] = planBackfill([usd(range(0, 364).map(at))]);
    expect(requestedDays(request)).toEqual([0, 30, 60, 90, 120, 150, 180, 210]);
  });

  it('should ask for one day a week once every month has a rate', () => {
    const [request] = planBackfill([usd(range(0, 59).map(at), [price(0), price(30)])]);
    expect(requestedDays(request)).toEqual([7, 14, 21, 37, 44, 51, 58]);
  });

  it('should fill every day last, on a daily grid that skips the days in between', () => {
    expect(planBackfill([usd([at(10), at(12), at(13)], [price(9)])])).toEqual([{
      asset: 'USD',
      excludeTimestamps: [11 * SECONDS_PER_DAY],
      fromTimestamp: 10 * SECONDS_PER_DAY,
      toTimestamp: 13 * SECONDS_PER_DAY,
    }]);
  });

  it('should ask for a single day as a two-day range without the second day, which the backend accepts', () => {
    expect(planBackfill([usd([at(10)])])).toEqual([{
      asset: 'USD',
      excludeTimestamps: [11 * SECONDS_PER_DAY],
      fromTimestamp: 10 * SECONDS_PER_DAY,
      toTimestamp: 11 * SECONDS_PER_DAY,
    }]);
  });

  it('should cover at most a few days per request, earliest first', () => {
    const [request] = planBackfill([usd(range(0, 19).map(at), [price(0), price(7), price(14)])]);
    expect(requestedDays(request)).toEqual([1, 2, 3, 4, 5, 8, 9, 10]);
    expect(requestedDays(request)).toHaveLength(DAYS_PER_REQUEST);
  });

  it('should leave out times with a price within a day, or known to have none', () => {
    const [request] = planBackfill([usd([at(10), at(11), at(12)], [price(10)], [11 * SECONDS_PER_DAY])]);
    expect(requestedDays(request)).toEqual([12]);
  });

  it('should ask for nothing once every time is settled', () => {
    expect(planBackfill([usd([at(10)], [price(10)])])).toEqual([]);
  });

  it('should give the UTC day start of a time', () => {
    expect(dayStart(at(3))).toBe(3 * SECONDS_PER_DAY);
  });
});
