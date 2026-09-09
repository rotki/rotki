import { describe, expect, it } from 'vitest';
import {
  leadingSortColumn,
  pageCount,
  sortDirection,
  toggledSort,
  toSortArray,
} from '@/modules/history/events/components/history-events-table-header';

describe('toSortArray', () => {
  it('should wrap a single entry', () => {
    expect(toSortArray({ column: 'timestamp', direction: 'asc' }))
      .toEqual([{ column: 'timestamp', direction: 'asc' }]);
  });

  it('should pass a list through', () => {
    const sort = [{ column: 'timestamp', direction: 'asc' }] as const;

    expect(toSortArray([...sort])).toEqual(sort);
  });

  it('should read an unsorted table as empty', () => {
    expect(toSortArray(undefined)).toEqual([]);
  });

  it('should read an empty list as empty', () => {
    expect(toSortArray([])).toEqual([]);
  });
});

describe('leadingSortColumn', () => {
  it('should report the column when it leads the sort', () => {
    expect(leadingSortColumn({ column: 'timestamp', direction: 'asc' }, 'timestamp')).toBe('timestamp');
  });

  it('should report nothing when another column leads', () => {
    expect(leadingSortColumn({ column: 'location', direction: 'asc' }, 'timestamp')).toBeUndefined();
  });

  /** The header offers one control, so a column further down the sort is not the one it shows. */
  it('should report nothing when the column only follows another', () => {
    const sort = [
      { column: 'location', direction: 'asc' },
      { column: 'timestamp', direction: 'asc' },
    ] as const;

    expect(leadingSortColumn([...sort], 'timestamp')).toBeUndefined();
  });

  it('should report nothing for an unsorted table', () => {
    expect(leadingSortColumn(undefined, 'timestamp')).toBeUndefined();
  });
});

describe('sortDirection', () => {
  it('should report the direction in force', () => {
    expect(sortDirection({ column: 'timestamp', direction: 'asc' })).toBe('asc');
  });

  it('should default an unsorted table to descending', () => {
    expect(sortDirection(undefined)).toBe('desc');
  });
});

describe('toggledSort', () => {
  it('should reverse a column already sorted ascending', () => {
    expect(toggledSort({ column: 'timestamp', direction: 'asc' }, 'timestamp'))
      .toEqual([{ column: 'timestamp', direction: 'desc' }]);
  });

  it('should reverse a column already sorted descending', () => {
    expect(toggledSort({ column: 'timestamp', direction: 'desc' }, 'timestamp'))
      .toEqual([{ column: 'timestamp', direction: 'asc' }]);
  });

  /** Newest first is what a table of events is expected to open on. */
  it('should start an unsorted table descending', () => {
    expect(toggledSort(undefined, 'timestamp')).toEqual([{ column: 'timestamp', direction: 'desc' }]);
  });

  it('should start descending when another column held the sort', () => {
    expect(toggledSort({ column: 'location', direction: 'asc' }, 'timestamp'))
      .toEqual([{ column: 'timestamp', direction: 'desc' }]);
  });

  it('should replace a multi-column sort rather than add to it', () => {
    const sort = [
      { column: 'timestamp', direction: 'asc' },
      { column: 'location', direction: 'asc' },
    ] as const;

    expect(toggledSort([...sort], 'timestamp')).toHaveLength(1);
  });

  it('should leave the sort it was handed unchanged', () => {
    const sort = [{ column: 'timestamp' as const, direction: 'asc' as const }];

    toggledSort(sort, 'timestamp');

    expect(sort).toEqual([{ column: 'timestamp', direction: 'asc' }]);
  });
});

describe('pageCount', () => {
  it('should count the pages the rows fill', () => {
    expect(pageCount(25, 10)).toBe(3);
  });

  it('should count an exactly filled last page once', () => {
    expect(pageCount(20, 10)).toBe(2);
  });

  it('should report no pages for no rows', () => {
    expect(pageCount(0, 10)).toBe(0);
  });

  /** Dividing by a zero page size would otherwise make the last-page control unreachable. */
  it('should report no pages rather than infinity for a zero page size', () => {
    expect(pageCount(25, 0)).toBe(0);
  });
});
