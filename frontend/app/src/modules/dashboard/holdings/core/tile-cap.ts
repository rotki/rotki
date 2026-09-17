import type { BigNumber } from '@rotki/common';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

interface TileGrid {
  readonly minWidth: number;
  readonly gap: number;
  readonly rows: number;
}

/**
 * How many tiles fit in the given rows of an `auto-fill` grid.
 *
 * @remarks
 * Mirrors `repeat(auto-fill, minmax(minWidth, 1fr))`: a column needs `minWidth`, and every column
 * after the first also needs a gap. Always at least one column, so a narrow container still shows
 * one tile per row.
 *
 * @param width - the grid's content width in pixels
 */
export function visibleTileCount(width: number, { gap, minWidth, rows }: TileGrid): number {
  const columns = Math.max(1, Math.floor((width + gap) / (minWidth + gap)));
  return columns * rows;
}

interface Split<T> {
  readonly visible: readonly T[];
  readonly hidden: readonly T[];
  readonly hiddenValue: BigNumber;
}

/** Splits items at `count`, totalling what the "show more" row stands for. */
export function splitVisible<T extends { readonly value: BigNumber }>(items: readonly T[], count: number): Split<T> {
  const hidden = items.slice(count);
  return {
    hidden,
    hiddenValue: bigNumberSum(hidden.map(item => item.value)),
    visible: items.slice(0, count),
  };
}
