import type { KnownPrice } from '@/modules/statistics/pricing/price-series';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { type BackfillAsset, DAYS_PER_REQUEST, dayStart, planBackfill } from '@/modules/statistics/pricing/backfill-plan';

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

describe('modules/statistics/pricing/backfill-plan', () => {
  it('should ask for the days of the requested times, skipping the days in between', () => {
    expect(planBackfill([usd([at(10), at(12), at(13)])])).toEqual([{
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
    const times = Array.from({ length: 20 }, (_, day) => at(day));
    const [request] = planBackfill([usd(times)]);
    expect(request.fromTimestamp).toBe(0);
    expect(request.toTimestamp).toBe((DAYS_PER_REQUEST - 1) * SECONDS_PER_DAY);
  });

  it('should leave out times with a price within a day, or known to have none', () => {
    const [request] = planBackfill([usd([at(10), at(11), at(12)], [price(10)], [11 * SECONDS_PER_DAY])]);
    expect(request).toMatchObject({ excludeTimestamps: [13 * SECONDS_PER_DAY], fromTimestamp: 12 * SECONDS_PER_DAY, toTimestamp: 13 * SECONDS_PER_DAY });
  });

  it('should ask for nothing once every time is settled', () => {
    expect(planBackfill([usd([at(10)], [price(10)])])).toEqual([]);
  });

  it('should give the UTC day start of a time', () => {
    expect(dayStart(at(3))).toBe(3 * SECONDS_PER_DAY);
  });
});
