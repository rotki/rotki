import type { ComputedRef } from 'vue';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { flatten } from 'es-toolkit';

interface UseCompleteEventsReturn {
  /**
   * Returns ALL events in a group as a flat array, including events with ignored assets.
   * Subgroups (swap/matched-movement arrays) are flattened into the result.
   *
   * Example: `[approve, [swapIn, swapOut]]` → `[approve, swapIn, swapOut]`
   */
  getGroupEvents: (groupId: string) => HistoryEventEntry[];
  /**
   * Given the displayed events of a swap/matched-movement subgroup, returns the
   * complete version of that subgroup from {@link completeEventsMapped} (which may
   * include additional hidden/ignored events not present in the displayed set).
   *
   * Use this when you already have the subgroup array (e.g. from a `swap-row`).
   *
   * Example: displayed `[swapIn]` → complete `[swapIn, swapOut_ignored]`
   */
  getCompleteSubgroupEvents: (displayedEvents: HistoryEventEntry[]) => HistoryEventEntry[];
  /**
   * Given a single event, determines the correct set of events for editing/deleting:
   * - If the event belongs to a subgroup (swap/matched-movement), returns only that subgroup.
   * - Otherwise, falls back to all events in the group via {@link getGroupEvents}.
   *
   * Use this when you have a single event (e.g. from an `event-row`) and need to
   * determine whether it's part of a subgroup or standalone.
   */
  getCompleteEventsForItem: (groupId: string, event: HistoryEventEntry) => HistoryEventEntry[];
}

/**
 * Provides helpers for resolving the correct set of complete events
 * (including hidden/ignored) for editing and deleting grouped events.
 */
export function useCompleteEvents(
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>,
): UseCompleteEventsReturn {
  function getGroupEvents(groupId: string): HistoryEventEntry[] {
    const groupEvents = get(completeEventsMapped)[groupId] || [];
    return flatten(groupEvents);
  }

  /**
   * Precomputed lookup from event identifier to its complete subgroup.
   * Maps each event inside a subgroup (array) to the full subgroup array for O(1) lookups.
   */
  const subgroupByEventId = computed<Map<number, HistoryEventEntry[]>>(() => {
    const map = new Map<number, HistoryEventEntry[]>();

    for (const rows of Object.values(get(completeEventsMapped))) {
      for (const row of rows) {
        if (Array.isArray(row)) {
          for (const event of row)
            map.set(event.identifier, row);
        }
      }
    }

    return map;
  });

  function getCompleteSubgroupEvents(displayedEvents: HistoryEventEntry[]): HistoryEventEntry[] {
    const first = displayedEvents[0];
    if (first) {
      const subgroup = get(subgroupByEventId).get(first.identifier);
      if (subgroup)
        return subgroup;
    }
    return displayedEvents;
  }

  function getCompleteEventsForItem(groupId: string, event: HistoryEventEntry): HistoryEventEntry[] {
    return get(subgroupByEventId).get(event.identifier) ?? getGroupEvents(groupId);
  }

  return {
    getCompleteEventsForItem,
    getCompleteSubgroupEvents,
    getGroupEvents,
  };
}
