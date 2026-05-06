import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { computeNetValueDelta } from '@/modules/dashboard/graph/net-value-stats';

describe('computeNetValueDelta', () => {
  const times = [1000, 2000, 3000, 4000, 5000];
  const data = [10, 20, 30, 40, 50].map(v => bigNumberify(v));

  it('should match legacy behaviour when no zoom is set', () => {
    const result = computeNetValueDelta(data, times, bigNumberify(60));
    expect(result.startingValue.toNumber()).toBe(10);
    expect(result.endValue.toNumber()).toBe(60);
    expect(result.balanceDelta.toNumber()).toBe(50);
  });

  it('should match legacy behaviour when zoom covers the full range', () => {
    const result = computeNetValueDelta(
      data,
      times,
      bigNumberify(60),
      { end: 5000, start: 1000 },
    );
    expect(result.startingValue.toNumber()).toBe(10);
    expect(result.endValue.toNumber()).toBe(60);
    expect(result.balanceDelta.toNumber()).toBe(50);
  });

  it('should derive start and end from the visible window when zoomed', () => {
    const result = computeNetValueDelta(
      data,
      times,
      bigNumberify(60),
      { end: 4000, start: 2000 },
    );
    expect(result.startingValue.toNumber()).toBe(20);
    expect(result.endValue.toNumber()).toBe(40);
    expect(result.balanceDelta.toNumber()).toBe(20);
  });

  it('should produce a negative delta when the window value drops', () => {
    const dropping = [50, 40, 30, 20, 10].map(v => bigNumberify(v));
    const result = computeNetValueDelta(
      dropping,
      times,
      bigNumberify(10),
      { end: 5000, start: 3000 },
    );
    expect(result.startingValue.toNumber()).toBe(30);
    expect(result.endValue.toNumber()).toBe(10);
    expect(result.balanceDelta.toNumber()).toBe(-20);
  });

  it('should skip leading zeros inside the zoom window', () => {
    const sparse = [0, 0, 25, 30, 50].map(v => bigNumberify(v));
    const result = computeNetValueDelta(
      sparse,
      times,
      bigNumberify(60),
      { end: 5000, start: 1000 },
    );
    // Full range so legacy path runs and skips leading zeros.
    expect(result.startingValue.toNumber()).toBe(25);
    expect(result.endValue.toNumber()).toBe(60);
  });

  it('should skip leading zeros inside a partial zoom window', () => {
    const sparse = [10, 0, 0, 40, 50].map(v => bigNumberify(v));
    const result = computeNetValueDelta(
      sparse,
      times,
      bigNumberify(60),
      { end: 4000, start: 2000 },
    );
    expect(result.startingValue.toNumber()).toBe(40);
    expect(result.endValue.toNumber()).toBe(40);
    expect(result.balanceDelta.toNumber()).toBe(0);
  });

  it('should return zeros for an empty dataset', () => {
    const result = computeNetValueDelta([], [], bigNumberify(0));
    expect(result.startingValue.toNumber()).toBe(0);
    expect(result.endValue.toNumber()).toBe(0);
    expect(result.balanceDelta.toNumber()).toBe(0);
  });

  it('should return zeros when the zoom window contains no datapoints', () => {
    const result = computeNetValueDelta(
      data,
      times,
      bigNumberify(60),
      { end: 999, start: 100 },
    );
    expect(result.startingValue.toNumber()).toBe(0);
    expect(result.endValue.toNumber()).toBe(0);
    expect(result.balanceDelta.toNumber()).toBe(0);
  });
});
