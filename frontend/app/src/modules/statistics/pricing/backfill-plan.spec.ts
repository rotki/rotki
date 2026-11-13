import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { type BackfillAsset, DAYS_PER_REQUEST, dayStart, planBackfill } from '@/modules/statistics/pricing/backfill-plan';
import { DAY_SECONDS, type KnownPrice } from '@/modules/statistics/pricing/price-series';

const NOON = DAY_SECONDS / 2;

function at(day: number): number {
  return day * DAY_SECONDS + NOON;
}

function price(day: number): KnownPrice {
  return { price: bigNumberify(1), time: day * DAY_SECONDS };
}

function usd(times: number[], known: KnownPrice[] = [], failed: number[] = []): BackfillAsset {
  return { asset: 'USD', failed, known, times };
}

describe('modules/statistics/pricing/backfill-plan', () => {
  it('should ask for the days of the requested times, skipping the days in between', () => {
    expect(planBackfill([usd([at(10), at(12), at(13)])])).toEqual([{
      asset: 'USD',
      excludeTimestamps: [11 * DAY_SECONDS],
      fromTimestamp: 10 * DAY_SECONDS,
      interval: DAY_SECONDS,
      toTimestamp: 13 * DAY_SECONDS,
    }]);
  });

  it('should ask for a single day as a two-day range without the second day, which the backend accepts', () => {
    expect(planBackfill([usd([at(10)])])).toEqual([{
      asset: 'USD',
      excludeTimestamps: [11 * DAY_SECONDS],
      fromTimestamp: 10 * DAY_SECONDS,
      interval: DAY_SECONDS,
      toTimestamp: 11 * DAY_SECONDS,
    }]);
  });

  it('should cover at most a few days per request, earliest first', () => {
    const times = Array.from({ length: 20 }, (_, day) => at(day));
    const [request] = planBackfill([usd(times)]);
    expect(request.fromTimestamp).toBe(0);
    expect(request.toTimestamp).toBe((DAYS_PER_REQUEST - 1) * DAY_SECONDS);
  });

  it('should leave out times with a price within a day, or known to have none', () => {
    const [request] = planBackfill([usd([at(10), at(11), at(12)], [price(10)], [11 * DAY_SECONDS])]);
    expect(request).toMatchObject({ excludeTimestamps: [13 * DAY_SECONDS], fromTimestamp: 12 * DAY_SECONDS, toTimestamp: 13 * DAY_SECONDS });
  });

  it('should ask for nothing once every time is settled', () => {
    expect(planBackfill([usd([at(10)], [price(10)])])).toEqual([]);
  });

  it('should give the UTC day start of a time', () => {
    expect(dayStart(at(3))).toBe(3 * DAY_SECONDS);
  });
});
