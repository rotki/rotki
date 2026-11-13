import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  ANCHOR_COUNT,
  type BackfillAsset,
  type BackfillRange,
  planBackfill,
  sampleInterval,
} from '@/modules/statistics/pricing/backfill-plan';
import { DAY_SECONDS, type KnownPrice } from '@/modules/statistics/pricing/price-series';

const range: BackfillRange = { end: 70 * DAY_SECONDS, start: 0 };
const anchorStep = 10 * DAY_SECONDS;

function anchors(price: (index: number) => number): KnownPrice[] {
  return Array.from({ length: ANCHOR_COUNT }, (_, index) => ({ price: bigNumberify(price(index)), time: index * anchorStep }));
}

function asset(name: string, heldValue: number, known: KnownPrice[] = [], failed: number[] = []): BackfillAsset {
  return { asset: name, failed, heldValue: bigNumberify(heldValue), known };
}

describe('modules/statistics/pricing/backfill-plan', () => {
  it('should refine to daily prices on short ranges and weekly on long ones', () => {
    expect(sampleInterval(range)).toBe(DAY_SECONDS);
    expect(sampleInterval({ end: 365 * DAY_SECONDS, start: 0 })).toBe(7 * DAY_SECONDS);
  });

  it('should ask for anchors first, largest holding first, in one request per asset', () => {
    const requests = planBackfill([asset('ETH', 100), asset('BTC', 900)], range, 5);
    expect(requests.map(request => [request.asset, request.kind])).toEqual([['BTC', 'anchor'], ['ETH', 'anchor']]);
    expect(requests[0]).toMatchObject({ fromTimestamp: 0, interval: anchorStep, toTimestamp: 70 * DAY_SECONDS });
  });

  it('should not ask again for anchors already cached or known to have no price', () => {
    const known = anchors(() => 10).slice(0, 4);
    const [request] = planBackfill([asset('BTC', 1, known, [4 * anchorStep])], range, 1);
    expect(request.excludeTimestamps).toEqual([0, anchorStep, 2 * anchorStep, 3 * anchorStep, 4 * anchorStep]);
  });

  it('should stop at the anchors when the price did not move', () => {
    expect(planBackfill([asset('USDC', 1000, anchors(() => 1))], range, 5)).toEqual([]);
  });

  it('should split the gap with the largest price move, asking only for its midpoint', () => {
    const known = anchors(index => (index === 3 ? 40 : 10));
    const [request] = planBackfill([asset('BTC', 1, known)], range, 1);
    expect(request).toMatchObject({
      excludeTimestamps: [2 * anchorStep],
      fromTimestamp: 2 * anchorStep,
      interval: anchorStep / 2,
      kind: 'refine',
      toTimestamp: 2 * anchorStep + anchorStep / 2,
    });
  });

  it('should refine larger holdings before smaller ones with the same move', () => {
    const moving = anchors(index => (index % 2 === 0 ? 10 : 20));
    const requests = planBackfill([asset('SMALL', 10, moving), asset('LARGE', 990, moving)], range, 2);
    expect(requests.map(request => request.asset)).toEqual(['LARGE', 'SMALL']);
  });

  it('should skip assets that never make up a meaningful share', () => {
    const requests = planBackfill([asset('DUST', 0.0001), asset('BTC', 1000)], range, 5);
    expect(requests.map(request => request.asset)).toEqual(['BTC']);
  });

  it('should stop once gaps are narrower than two chart samples', () => {
    const dense = Array.from({ length: 71 }, (_, day) => ({ price: bigNumberify(day % 2 === 0 ? 10 : 20), time: day * DAY_SECONDS }));
    expect(planBackfill([asset('BTC', 1, dense)], range, 5)).toEqual([]);
  });

  it('should ask for a single point once, for a range under a day', () => {
    const at = 10 * DAY_SECONDS;
    expect(planBackfill([asset('USD', 1)], { end: at, start: at }, 5)).toEqual([{
      asset: 'USD',
      excludeTimestamps: [],
      fromTimestamp: at,
      interval: DAY_SECONDS,
      kind: 'anchor',
      score: Number.POSITIVE_INFINITY,
      toTimestamp: at,
    }]);
    expect(planBackfill([asset('USD', 1, [{ price: bigNumberify('0.9'), time: at + 3600 }])], { end: at, start: at }, 5)).toEqual([]);
  });

  it('should return nothing for a reversed range or nothing held', () => {
    expect(planBackfill([asset('BTC', 1)], { end: 0, start: 10 }, 5)).toEqual([]);
    expect(planBackfill([asset('BTC', 0)], range, 5)).toEqual([]);
  });
});
