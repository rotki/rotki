import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { splitVisible, visibleTileCount } from './tile-cap';

const grid = { gap: 16, minWidth: 180, rows: 2 };

describe('visibleTileCount', () => {
  it.each([
    { columns: 1, width: 100 },
    { columns: 1, width: 375 },
    { columns: 2, width: 376 },
    { columns: 5, width: 964 },
    { columns: 6, width: 1160 },
  ])('should fit $columns columns in $width px', ({ columns, width }) => {
    expect(visibleTileCount(width, grid)).toBe(columns * 2);
  });
});

describe('splitVisible', () => {
  const items = [5, 4, 3, 2].map(value => ({ value: bigNumberify(value) }));

  it('should split at the count and total what is hidden', () => {
    const { hidden, hiddenValue, visible } = splitVisible(items, 2);

    expect(visible).toHaveLength(2);
    expect(hidden).toHaveLength(2);
    expect(hiddenValue.toFixed()).toBe('5');
  });

  it('should hide nothing when everything fits', () => {
    const { hidden, hiddenValue, visible } = splitVisible(items, 10);

    expect(visible).toHaveLength(4);
    expect(hidden).toEqual([]);
    expect(hiddenValue.isZero()).toBe(true);
  });
});
