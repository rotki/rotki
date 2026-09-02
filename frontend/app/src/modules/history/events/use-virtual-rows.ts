import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';

export const ROW_HEIGHTS = {
  'group-header': 48,
  'event-row': 72,
  'event-placeholder': 72,
  'swap-row': 72,
  'matched-movement-row': 72,
  'swap-collapse': 36,
  'matched-movement-collapse': 36,
  'load-more': 36,
} as const;

/** Row heights for the mobile card layout, which stacks the same rows taller than the table does. */
const CARD_HEIGHTS = {
  'group-header': 72,
  'event-row': 140,
  'event-placeholder': 140,
  'swap-row': 160,
  'matched-movement-row': 160,
  'swap-collapse': 40,
  'matched-movement-collapse': 40,
  'load-more': 40,
} as const;

const INITIAL_EVENTS_LIMIT = 6;
const LOAD_MORE_INCREMENT = 6;

interface GroupHeaderRow {
  type: 'group-header';
  groupId: string;
  data: HistoryEventEntry;
}

interface EventDetailRow {
  type: 'event-row';
  groupId: string;
  data: HistoryEventEntry;
  index: number;
  /**
   * True when this row is one leg of an expanded linked subgroup, which is either a matched
   * movement or a matched bridge transfer.
   */
  linkedLeg?: boolean;
}

interface EventPlaceholderRow {
  type: 'event-placeholder';
  groupId: string;
  index: number;
}

interface SwapRow {
  type: 'swap-row';
  groupId: string;
  events: HistoryEventEntry[];
  index: number;
  swapKey: string;
}

interface SwapCollapseRow {
  type: 'swap-collapse';
  groupId: string;
  swapKey: string;
  /** Primary event id — the subgroup's identity in the DOM, so a test can name one swap. */
  subgroupId?: number;
  eventCount: number;
  /** True when the subgroup is a matched bridge transfer rather than a swap. */
  bridge: boolean;
}

interface MatchedMovementRow {
  type: 'matched-movement-row';
  groupId: string;
  events: HistoryEventEntry[];
  index: number;
  movementKey: string;
}

interface MatchedMovementCollapseRow {
  type: 'matched-movement-collapse';
  groupId: string;
  movementKey: string;
  eventCount: number;
}

interface LoadMoreRow {
  type: 'load-more';
  groupId: string;
  hiddenCount: number;
  totalCount: number;
}

export type VirtualRow = GroupHeaderRow | EventDetailRow | EventPlaceholderRow | SwapRow | SwapCollapseRow | MatchedMovementRow | MatchedMovementCollapseRow | LoadMoreRow;

/**
 * Checks if an array of events represents a matched asset movement (deposit/withdrawal)
 * rather than a swap. A matched movement contains at least one event with
 * entryType === ASSET_MOVEMENT_EVENT (the exchange side of the transfer).
 */
function isMatchedMovementGroup(events: HistoryEventEntry[]): boolean {
  return events.some(e => e.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT);
}

/**
 * Checks if an array of events is a joined matched bridge transfer: the two
 * legs of a cross-chain bridge, both carrying the bridge event subtype.
 */
function isMatchedBridgeGroup(events: HistoryEventEntry[]): boolean {
  return events.some(e => e.eventSubtype === 'bridge');
}

/**
 * Identity of a subgroup (a swap or a matched movement), for remembering that it is expanded.
 *
 * Keyed by the primary event, never by position. A positional key does not survive the list
 * changing underneath it: any shift collapses an expanded subgroup or hands its state to whichever
 * subgroup landed on that index, and a background refetch is enough to do it.
 *
 * The primary event outlives the edits that break a positional key: deleting a swap's fee leaves the
 * swap intact, and deleting the primary event takes the whole subgroup with it.
 */
function subgroupKey(groupId: string, events: HistoryEventEntry[]): string {
  return `${groupId}-${events[0]?.identifier ?? 0}`;
}

interface UseVirtualRowsReturn {
  flattenedRows: ComputedRef<VirtualRow[]>;
  groupVisibleCounts: DeepReadonly<Ref<Map<string, number>>>;
  expandedSwaps: DeepReadonly<Ref<Set<string>>>;
  expandedMovements: DeepReadonly<Ref<Set<string>>>;
  loadMoreEvents: (groupId: string) => void;
  toggleSwapExpanded: (swapKey: string) => void;
  toggleMovementExpanded: (movementKey: string) => void;
  getRowHeight: (index: number) => number;
  getCardHeight: (index: number) => number;
}

export function useVirtualRows(
  groups: ComputedRef<HistoryEventEntry[]>,
  eventsByGroup: ComputedRef<Record<string, HistoryEventRow[]>>,
  isSubgroupIncomplete: (events: HistoryEventEntry[]) => boolean,
): UseVirtualRowsReturn {
  // Track how many items are visible per group (beyond initial limit)
  const groupVisibleCounts = shallowRef<Map<string, number>>(new Map());
  const expandedSwaps = shallowRef<Set<string>>(new Set());
  // Track which matched movement rows are expanded (key: see `subgroupKey`)
  const expandedMovements = shallowRef<Set<string>>(new Set());

  const flattenedRows = computed<VirtualRow[]>(() => {
    const rows: VirtualRow[] = [];
    const groupsValue = get(groups);
    const eventsMap = get(eventsByGroup);
    const visibleCounts = get(groupVisibleCounts);
    const expandedSwapsSet = get(expandedSwaps);
    const expandedMovementsSet = get(expandedMovements);

    for (const group of groupsValue) {
      const groupId = group.groupIdentifier;

      rows.push({
        type: 'group-header',
        groupId,
        data: group,
      });

      const allEvents = eventsMap[groupId] || [];
      const customLimit = visibleCounts.get(groupId);
      const limit = customLimit ?? INITIAL_EVENTS_LIMIT;

      // If events not loaded yet, show placeholders based on groupedEventsNum
      if (allEvents.length === 0 && group.groupedEventsNum) {
        const placeholderCount = Math.min(group.groupedEventsNum, limit);
        for (let i = 0; i < placeholderCount; i++) {
          rows.push({
            type: 'event-placeholder',
            groupId,
            index: i,
          });
        }
        continue;
      }

      const visibleEvents = allEvents.slice(0, limit);

      visibleEvents.forEach((event, i) => {
        // Handle array (subgroup - could be swap or matched movement)
        if (Array.isArray(event)) {
          const forcedOpenWithoutCollapseControls = isSubgroupIncomplete(event);

          // Check if this is a matched asset movement (not a swap)
          if (isMatchedMovementGroup(event)) {
            const movementKey = subgroupKey(groupId, event);
            const isMovementExpanded = forcedOpenWithoutCollapseControls || expandedMovementsSet.has(movementKey);

            if (isMovementExpanded) {
              if (!forcedOpenWithoutCollapseControls) {
                rows.push({
                  type: 'matched-movement-collapse',
                  groupId,
                  movementKey,
                  eventCount: event.length,
                });
              }

              event.forEach((subEvent, subIndex) => {
                rows.push({
                  type: 'event-row',
                  groupId,
                  data: subEvent,
                  index: subIndex,
                  linkedLeg: true,
                });
              });
            }
            else {
              // Collapsed: show as combined matched movement row
              rows.push({
                type: 'matched-movement-row',
                groupId,
                events: event,
                index: i,
                movementKey,
              });
            }
          }
          else {
            const swapKey = subgroupKey(groupId, event);
            const isSwapExpanded = forcedOpenWithoutCollapseControls || expandedSwapsSet.has(swapKey);
            const bridge = isMatchedBridgeGroup(event);

            if (isSwapExpanded) {
              if (!forcedOpenWithoutCollapseControls) {
                rows.push({
                  type: 'swap-collapse',
                  groupId,
                  swapKey,
                  subgroupId: event[0]?.identifier,
                  eventCount: event.length,
                  bridge,
                });
              }

              event.forEach((subEvent, subIndex) => {
                rows.push({
                  type: 'event-row',
                  groupId,
                  data: subEvent,
                  index: subIndex,
                  linkedLeg: bridge,
                });
              });
            }
            else {
              // Collapsed: show as combined swap row
              rows.push({
                type: 'swap-row',
                groupId,
                events: event,
                index: i,
                swapKey,
              });
            }
          }
        }
        else {
          rows.push({
            type: 'event-row',
            groupId,
            data: event,
            index: i,
          });
        }
      });

      // 3. Load more row (if there are still hidden events)
      const hiddenCount = allEvents.length - limit;
      if (hiddenCount > 0) {
        rows.push({
          type: 'load-more',
          groupId,
          hiddenCount,
          totalCount: allEvents.length,
        });
      }
    }

    return rows;
  });

  function loadMoreEvents(groupId: string): void {
    const visibleCounts = new Map(get(groupVisibleCounts));
    const currentLimit = visibleCounts.get(groupId) ?? INITIAL_EVENTS_LIMIT;
    visibleCounts.set(groupId, currentLimit + LOAD_MORE_INCREMENT);
    set(groupVisibleCounts, visibleCounts);
  }

  function toggleSwapExpanded(swapKey: string): void {
    const expanded = new Set(get(expandedSwaps));
    if (expanded.has(swapKey)) {
      expanded.delete(swapKey);
    }
    else {
      expanded.add(swapKey);
    }
    set(expandedSwaps, expanded);
  }

  function toggleMovementExpanded(movementKey: string): void {
    const expanded = new Set(get(expandedMovements));
    if (expanded.has(movementKey)) {
      expanded.delete(movementKey);
    }
    else {
      expanded.add(movementKey);
    }
    set(expandedMovements, expanded);
  }

  function getRowHeight(index: number): number {
    const row = get(flattenedRows)[index];
    return row ? ROW_HEIGHTS[row.type] : ROW_HEIGHTS['event-row'];
  }

  function getCardHeight(index: number): number {
    const row = get(flattenedRows)[index];
    return row ? CARD_HEIGHTS[row.type] : CARD_HEIGHTS['event-row'];
  }

  return {
    expandedMovements: readonly(expandedMovements),
    expandedSwaps: readonly(expandedSwaps),
    flattenedRows,
    getCardHeight,
    getRowHeight,
    groupVisibleCounts: readonly(groupVisibleCounts),
    loadMoreEvents,
    toggleMovementExpanded,
    toggleSwapExpanded,
  };
}
