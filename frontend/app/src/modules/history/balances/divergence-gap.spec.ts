import { describe, expect, it } from 'vitest';
import { divergenceGap, GapUnit } from '@/modules/history/balances/divergence-gap';

const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

describe('divergenceGap', () => {
  it('should round days to the nearest whole day', () => {
    expect(divergenceGap(1000, 1000 + (9 * DAY) + (22 * HOUR))).toMatchObject({ count: 10, unit: GapUnit.DAYS });
    expect(divergenceGap(1000, 1000 + (9 * DAY) + (11 * HOUR))).toMatchObject({ count: 9, unit: GapUnit.DAYS });
  });

  it('should round hours for a gap under a day', () => {
    expect(divergenceGap(1000, 1000 + (5 * HOUR) + (31 * MINUTE))).toMatchObject({ count: 6, unit: GapUnit.HOURS });
    expect(divergenceGap(1000, 1000 + (5 * HOUR) + (29 * MINUTE))).toMatchObject({ count: 5, unit: GapUnit.HOURS });
  });

  it('should move up to the next unit when rounding reaches it, instead of reading 24 hours or 60 minutes', () => {
    expect(divergenceGap(1000, 1000 + (23 * HOUR) + (40 * MINUTE))).toMatchObject({ count: 1, unit: GapUnit.DAYS });
    expect(divergenceGap(1000, 1000 + (59 * MINUTE) + 40)).toMatchObject({ count: 1, unit: GapUnit.HOURS });
  });

  it('should round minutes for a gap under an hour, and give zero minutes under half a minute', () => {
    expect(divergenceGap(1000, 1000 + (12 * MINUTE) + 40)).toMatchObject({ count: 13, unit: GapUnit.MINUTES });
    expect(divergenceGap(1000, 1000 + 31)).toMatchObject({ count: 1, unit: GapUnit.MINUTES });
    expect(divergenceGap(1000, 1000 + 29)).toMatchObject({ count: 0, unit: GapUnit.MINUTES });
  });

  it('should mark a gap exact only when the count covers it to the second', () => {
    expect(divergenceGap(1000, 1000 + (3 * DAY))).toEqual({ count: 3, exact: true, unit: GapUnit.DAYS });
    expect(divergenceGap(1000, 1000 + (2 * HOUR))).toEqual({ count: 2, exact: true, unit: GapUnit.HOURS });
    expect(divergenceGap(1000, 1000 + (3 * DAY) + 1)).toEqual({ count: 3, exact: false, unit: GapUnit.DAYS });
    expect(divergenceGap(1000, 1000 + (23 * HOUR) + (40 * MINUTE))).toEqual({ count: 1, exact: false, unit: GapUnit.DAYS });
  });

  it('should not depend on the order of the two timestamps', () => {
    expect(divergenceGap(1000 + (2 * DAY), 1000)).toEqual({ count: 2, exact: true, unit: GapUnit.DAYS });
  });
});
