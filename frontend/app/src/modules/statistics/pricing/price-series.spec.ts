import { bigNumberify, PriceQuality } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { isFallbackQuality, type KnownPrice, nearestWithin, resolvePriceSeries } from '@/modules/statistics/pricing/price-series';

function point(day: number, price: number | string): KnownPrice {
  return { price: bigNumberify(price), time: day * SECONDS_PER_DAY };
}

function summary(resolved: ReturnType<typeof resolvePriceSeries>): [string, string | undefined][] {
  return resolved.map(item => [item.quality, item.price?.toFixed()]);
}

describe('modules/statistics/pricing/price-series', () => {
  describe('nearestWithin', () => {
    it('should pick the closer neighbour, preferring the earlier one on a tie', () => {
      const points = [point(1, 10), point(3, 30)];
      expect(nearestWithin(points, 2 * SECONDS_PER_DAY, SECONDS_PER_DAY)?.price.toFixed()).toBe('10');
      expect(nearestWithin(points, 2.5 * SECONDS_PER_DAY, SECONDS_PER_DAY)?.price.toFixed()).toBe('30');
    });

    it('should return nothing outside the tolerance', () => {
      expect(nearestWithin([point(1, 10)], 3 * SECONDS_PER_DAY, SECONDS_PER_DAY)).toBeUndefined();
    });
  });

  describe('resolvePriceSeries', () => {
    it('should use a cached price close to the time as exact', () => {
      const resolved = resolvePriceSeries([point(1, 10)], undefined, [SECONDS_PER_DAY + 3600]);
      expect(summary(resolved)).toEqual([[PriceQuality.EXACT, '10']]);
    });

    it('should carry the nearest earlier price forward across a gap', () => {
      const resolved = resolvePriceSeries([point(1, 10), point(9, 90)], undefined, [5 * SECONDS_PER_DAY]);
      expect(summary(resolved)).toEqual([[PriceQuality.CARRIED, '10']]);
    });

    it('should back-fill from the nearest later price before the first known one', () => {
      const resolved = resolvePriceSeries([point(5, 50), point(9, 90)], undefined, [SECONDS_PER_DAY]);
      expect(summary(resolved)).toEqual([[PriceQuality.BACK_FILLED, '50']]);
    });

    it('should use today\'s price only when nothing is cached', () => {
      const resolved = resolvePriceSeries([], bigNumberify(7), [SECONDS_PER_DAY]);
      expect(summary(resolved)).toEqual([[PriceQuality.CURRENT, '7']]);
    });

    it('should report missing, never zero, when no price exists at all', () => {
      const resolved = resolvePriceSeries([], bigNumberify(0), [SECONDS_PER_DAY]);
      expect(summary(resolved)).toEqual([[PriceQuality.MISSING, undefined]]);
    });

    it('should keep the order of the requested times', () => {
      const resolved = resolvePriceSeries([point(1, 10), point(3, 30)], undefined, [3 * SECONDS_PER_DAY, SECONDS_PER_DAY]);
      expect(resolved.map(item => item.price?.toFixed())).toEqual(['30', '10']);
    });
  });

  it('should say when the price it used was quoted, and nothing for today\'s price', () => {
    const resolved = resolvePriceSeries([point(1, 10)], bigNumberify(7), [SECONDS_PER_DAY, 5 * SECONDS_PER_DAY]);
    expect(resolved.map(item => item.time)).toEqual([SECONDS_PER_DAY, SECONDS_PER_DAY]);
    expect(resolvePriceSeries([], bigNumberify(7), [SECONDS_PER_DAY])[0].time).toBeUndefined();
  });

  it('should treat only exact as a real price', () => {
    expect(Object.values(PriceQuality).filter(quality => !isFallbackQuality(quality))).toEqual([PriceQuality.EXACT]);
  });
});
