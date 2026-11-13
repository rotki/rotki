import { describe, expect, it } from 'vitest';
import { estimatedBands } from '@/modules/dashboard/graph/net-value-estimated-bands';

describe('modules/dashboard/graph/net-value-estimated-bands', () => {
  it('should return no band when nothing is estimated', () => {
    expect(estimatedBands([1, 2, 3], undefined)).toEqual([]);
    expect(estimatedBands([1, 2, 3], [false, false, false])).toEqual([]);
  });

  it('should give one band per run, reaching halfway to the neighbouring points', () => {
    expect(estimatedBands([0, 10, 20, 30, 40, 50], [false, true, true, false, true, false]))
      .toEqual([{ end: 25, start: 5 }, { end: 45, start: 35 }]);
  });

  it('should stop a band at the first and last points of the series', () => {
    expect(estimatedBands([0, 10, 20], [true, false, true])).toEqual([{ end: 5, start: 0 }, { end: 20, start: 15 }]);
  });
});
