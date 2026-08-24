import type { AssetBalanceWithPrice } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';

type PricePendingCheck = (asset: string) => boolean;

type ValueRow = Pick<AssetBalanceWithPrice, 'asset' | 'breakdown'>;

interface UseValuePendingReturn {
  /** Whether a row's value should render as a loading state rather than a number. */
  isValuePending: (row: ValueRow) => boolean;
  /** Whether a total summed over `rows` is short of any of them. */
  isTotalPending: (rows: ValueRow[]) => boolean;
}

/**
 * A group is only as known as its worst member: a collection row sums several assets, so one
 * member without a price leaves the total short by that member's whole holding, with nothing in
 * the row to say so.
 */
export function isRowValuePending(row: ValueRow, isPricePending: PricePendingCheck): boolean {
  if (isPricePending(row.asset))
    return true;

  return (row.breakdown ?? []).some(member => isPricePending(member.asset));
}

export function isTotalValuePending(rows: ValueRow[], isPricePending: PricePendingCheck): boolean {
  return rows.some(row => isRowValuePending(row, isPricePending));
}

/**
 * Whether balance values can be shown yet.
 *
 * A value is only trustworthy once its price is. With a price a holding is valued as
 * `amount × price` over the whole of it; without one it falls back to the values the backend
 * attached to whichever chains have reported so far, which is a fraction of the amount rendered
 * beside it, and looks just as settled.
 */
export function useValuePending(): UseValuePendingReturn {
  const { isPricePending } = usePriceUtils();

  return {
    isTotalPending: (rows: ValueRow[]): boolean => isTotalValuePending(rows, isPricePending),
    isValuePending: (row: ValueRow): boolean => isRowValuePending(row, isPricePending),
  };
}
