import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import { useSmallValueEvents } from '@/modules/history/events/use-small-value-events';
import { useSetting } from '@/modules/settings/use-setting';

interface UseSmallValueRowsReturn<TRow> {
  /** Whether small value events are de-emphasized at all, which is when hiding them is offered. */
  enabled: ComputedRef<boolean>;
  /** The selection ids of the rows left out, empty unless hiding is on. */
  hiddenIds: ComputedRef<Set<string>>;
  /** The rows to present: all of them, or the ones worth at least the threshold while hiding. */
  visibleRows: ComputedRef<TRow[]>;
  /** The threshold, in the main currency, a row has to reach to stay listed. */
  threshold: ComputedRef<number>;
}

/**
 * Leaves the unmatched rows worth less than the small value threshold out of a matching panel, when
 * the user chose to hide them.
 *
 * @remarks
 * The matching panels hold every unmatched item client side, so unlike the paginated history table
 * they can drop rows without leaving a page short. While hiding is on every row is priced, not only
 * the ones in view, and a row whose price has not resolved yet stays listed until it has, so nothing
 * disappears on a guess.
 */
export function useSmallValueRows<TRow extends UnmatchedRow<unknown>>(
  rows: MaybeRefOrGetter<TRow[]>,
): UseSmallValueRowsReturn<TRow> {
  const { enabled, isSmallValue, threshold } = useSmallValueEvents();
  const hideSmallValueMovements = useSetting('hideSmallValueMovements');

  const hiddenIds = computed<Set<string>>(() => {
    if (!get(enabled) || !get(hideSmallValueMovements))
      return new Set<string>();

    return new Set<string>(toValue(rows).filter(row => isSmallValue(row.entry)).map(row => row.id));
  });

  const visibleRows = computed<TRow[]>(() => {
    const hidden = get(hiddenIds);
    const allRows = toValue(rows);
    return hidden.size === 0 ? allRows : allRows.filter(row => !hidden.has(row.id));
  });

  return {
    enabled,
    hiddenIds,
    threshold,
    visibleRows,
  };
}
