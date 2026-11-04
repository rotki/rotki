import type { Ref } from 'vue';
import type { PotentialMatchRow } from '@/modules/history/events/matching/types';

interface UsePotentialMatchSelectionReturn {
  isSelected: (row: PotentialMatchRow) => boolean;
  /** Adds the row's event to the selection, or removes it when it is already there. */
  toggle: (row: PotentialMatchRow) => void;
}

/**
 * Selection of potential matches by event identifier, shared by the table and the card views.
 *
 * @param selectedIds - the identifiers of the selected events, written in place by `toggle`
 */
export function usePotentialMatchSelection(selectedIds: Ref<number[]>): UsePotentialMatchSelectionReturn {
  function isSelected(row: PotentialMatchRow): boolean {
    return get(selectedIds).includes(row.entry.identifier);
  }

  function toggle(row: PotentialMatchRow): void {
    const identifier = row.entry.identifier;
    const ids = get(selectedIds);
    set(selectedIds, ids.includes(identifier) ? ids.filter(id => id !== identifier) : [...ids, identifier]);
  }

  return { isSelected, toggle };
}
