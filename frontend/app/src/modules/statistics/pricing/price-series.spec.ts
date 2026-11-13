import { bigNumberify, PriceQuality } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { DAY_SECONDS, isFallbackQuality, type KnownPrice, nearestWithin, resolvePriceSeries } from '@/modules/statistics/pricing/price-series';

function point(day: number, price: number | string): KnownPrice {
  return { price: bigNumberify(price), time: day * DAY_SECONDS };
}

function summary(resolved: ReturnType<typeof resolvePriceSeries>): [string, string | undefined][] {
  return resolved.map(item => [item.quality, item.price?.toFixed()]);
}

describe('modules/statistics/pricing/price-series', () => {
  describe('nearestWithin', () => {
    it('should pick the closer neighbour, preferring the earlier one on a tie', () => {
      const points = [point(1, 10), point(3, 30)];
      expect(nearestWithin(points, 2 * DAY_SECONDS, DAY_SECONDS)?.price.toFixed()).toBe('10');
      expect(nearestWithin(points, 2.5 * DAY_SECONDS, DAY_SECONDS)?.price.toFixed()).toBe('30');
    });

    it('should return nothing outside the tolerance', () => {
      expect(nearestWithin([point(1, 10)], 3 * DAY_SECONDS, DAY_SECONDS)).toBeUndefined();
    });
  });

  describe('resolvePriceSeries', () => {
    it('should use a cached price close to the time as exact', () => {
      const resolved = resolvePriceSeries({ direct: [point(1, 10)] }, [DAY_SECONDS + 3600]);
      expect(summary(resolved)).toEqual([[PriceQuality.EXACT, '10']]);
    });

    it('should derive a price through USD when the direct pair misses', () => {
      const resolved = resolvePriceSeries({
        direct: [],
        usdToMain: [point(2, '0.9')],
        viaUsd: [point(2, 100)],
      }, [2 * DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.DERIVED, '90']]);
    });

    it('should not derive when the USD rate is from another time', () => {
      const resolved = resolvePriceSeries({
        direct: [],
        usdToMain: [point(10, '0.9')],
        viaUsd: [point(2, 100)],
      }, [2 * DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.MISSING, undefined]]);
    });

    it('should prefer a direct price over a derived one at the same time', () => {
      const resolved = resolvePriceSeries({
        direct: [point(2, 95)],
        usdToMain: [point(2, '0.9')],
        viaUsd: [point(2, 100)],
      }, [2 * DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.EXACT, '95']]);
    });

    it('should carry the nearest earlier price forward across a gap', () => {
      const resolved = resolvePriceSeries({ direct: [point(1, 10), point(9, 90)] }, [5 * DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.CARRIED, '10']]);
    });

    it('should back-fill from the nearest later price before the first known one', () => {
      const resolved = resolvePriceSeries({ direct: [point(5, 50), point(9, 90)] }, [DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.BACK_FILLED, '50']]);
    });

    it('should use today\'s price only when nothing is cached', () => {
      const resolved = resolvePriceSeries({ current: bigNumberify(7), direct: [] }, [DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.CURRENT, '7']]);
    });

    it('should report missing, never zero, when no price exists at all', () => {
      const resolved = resolvePriceSeries({ current: bigNumberify(0), direct: [point(1, 0)] }, [DAY_SECONDS]);
      expect(summary(resolved)).toEqual([[PriceQuality.MISSING, undefined]]);
    });

    it('should keep the order of the requested times', () => {
      const resolved = resolvePriceSeries({ direct: [point(1, 10), point(3, 30)] }, [3 * DAY_SECONDS, DAY_SECONDS]);
      expect(resolved.map(item => item.price?.toFixed())).toEqual(['30', '10']);
    });
  });

  it('should treat only exact and derived as real prices', () => {
    expect(Object.values(PriceQuality).filter(quality => !isFallbackQuality(quality)))
      .toEqual([PriceQuality.EXACT, PriceQuality.DERIVED]);
  });
});
