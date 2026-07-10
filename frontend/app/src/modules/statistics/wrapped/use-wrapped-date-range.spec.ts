import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWrappedDateRange } from '@/modules/statistics/wrapped/use-wrapped-date-range';

describe('useWrappedDateRange', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it('should compute the unix range for a given year', () => {
    const { getYearRange } = useWrappedDateRange();
    const range = getYearRange(2023);
    expect(range.start).toBe(dayjs().year(2023).startOf('year').unix());
    expect(range.end).toBe(dayjs().year(2023).endOf('year').unix());
    expect(range.start).toBeLessThan(range.end);
  });

  it('should set the start and end refs when applying a year range', () => {
    const { end, setYearRange, start } = useWrappedDateRange();
    setYearRange(2022);
    expect(get(start)).toBe(dayjs().year(2022).startOf('year').unix());
    expect(get(end)).toBe(dayjs().year(2022).endOf('year').unix());
  });

  it('should expose start as undefined through startModel when zero', () => {
    const { startModel } = useWrappedDateRange();
    expect(get(startModel)).toBeUndefined();
  });

  it('should map startModel writes back onto the start ref', () => {
    const { start, startModel } = useWrappedDateRange();
    set(startModel, 1000);
    expect(get(start)).toBe(1000);
    expect(get(startModel)).toBe(1000);
  });

  it('should reset start to zero when startModel is set to undefined', () => {
    const { start, startModel } = useWrappedDateRange();
    set(startModel, 1000);
    set(startModel, undefined);
    expect(get(start)).toBe(0);
    expect(get(startModel)).toBeUndefined();
  });

  it('should not flag a valid range as invalid', () => {
    const { end, invalidRange, start } = useWrappedDateRange();
    set(start, 100);
    set(end, 200);
    expect(get(invalidRange)).toBe(false);
  });

  it('should flag a range where start is after end as invalid', () => {
    const { end, invalidRange, start } = useWrappedDateRange();
    set(start, 300);
    set(end, 200);
    expect(get(invalidRange)).toBe(true);
  });

  it('should not flag the range as invalid when either bound is unset', () => {
    const { end, invalidRange, start } = useWrappedDateRange();
    set(start, 300);
    set(end, 0);
    expect(get(invalidRange)).toBe(false);
  });

  it('should initialize the end date to now when it is unset', () => {
    const { end, initializeEndDate } = useWrappedDateRange();
    const before = dayjs().unix();
    initializeEndDate();
    expect(get(end)).toBeGreaterThanOrEqual(before);
  });

  it('should not override an already set end date on initialization', () => {
    const { end, initializeEndDate } = useWrappedDateRange();
    set(end, 12345);
    initializeEndDate();
    expect(get(end)).toBe(12345);
  });
});
