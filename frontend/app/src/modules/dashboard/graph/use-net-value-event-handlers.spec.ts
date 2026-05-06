import { describe, expect, it } from 'vitest';
import { readZoomFields, resolveZoomRange } from '@/modules/dashboard/graph/use-net-value-event-handlers';

describe('readZoomFields', () => {
  it('should read top-level fields when batch is absent (slider drag shape)', () => {
    expect(readZoomFields({ end: 80, endValue: 2000, start: 20, startValue: 1000 })).toEqual({
      end: 80,
      endValue: 2000,
      start: 20,
      startValue: 1000,
    });
  });

  it('should read batch[0] when present (inside-zoom shape)', () => {
    expect(readZoomFields({
      batch: [{ end: 90, endValue: 3000, start: 10, startValue: 500 }],
    })).toEqual({ end: 90, endValue: 3000, start: 10, startValue: 500 });
  });

  it('should accept percent-only batch entries (slider without axis values)', () => {
    expect(readZoomFields({ batch: [{ end: 75, start: 25 }] })).toEqual({
      end: 75,
      endValue: undefined,
      start: 25,
      startValue: undefined,
    });
  });

  it('should return undefined for non-object input', () => {
    expect(readZoomFields(undefined)).toBeUndefined();
    expect(readZoomFields(null)).toBeUndefined();
    expect(readZoomFields('event')).toBeUndefined();
  });

  it('should return undefined when batch is empty and no top-level fields are set', () => {
    expect(readZoomFields({ batch: [null] })).toBeUndefined();
    // empty batch falls through to the top-level read, which yields all-undefined fields
    expect(resolveZoomRange(readZoomFields({ batch: [] }), [1, 2])).toBeUndefined();
  });
});

describe('resolveZoomRange', () => {
  const times = [1000, 2000, 3000, 4000, 5000];

  it('should convert ms axis values to second-based range', () => {
    expect(resolveZoomRange({ endValue: 4000000, startValue: 2000000 }, times)).toEqual({
      end: 4000,
      start: 2000,
    });
  });

  it('should map percentage range against the times window when axis values are absent', () => {
    // 25%..75% of [1000, 5000] -> [2000, 4000]
    expect(resolveZoomRange({ end: 75, start: 25 }, times)).toEqual({ end: 4000, start: 2000 });
  });

  it('should prefer axis values when both shapes are present', () => {
    expect(resolveZoomRange({ end: 100, endValue: 3000000, start: 0, startValue: 1500000 }, times)).toEqual({
      end: 3000,
      start: 1500,
    });
  });

  it('should return undefined when only one bound is provided', () => {
    expect(resolveZoomRange({ start: 25 }, times)).toBeUndefined();
    expect(resolveZoomRange({ startValue: 1000 }, times)).toBeUndefined();
  });

  it('should return undefined when fields are missing or times empty', () => {
    expect(resolveZoomRange(undefined, times)).toBeUndefined();
    expect(resolveZoomRange({ end: 75, start: 25 }, [])).toBeUndefined();
  });
});
