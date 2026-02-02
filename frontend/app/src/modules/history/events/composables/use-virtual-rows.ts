import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
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

// Card heights for mobile layout
export const CARD_HEIGHTS = {
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

export type VirtualRowType = keyof typeof ROW_HEIGHTS;

export interface GroupHeaderRow {
  type: 'group-header';
  groupId: string;
  data: HistoryEventEntry;
}

export interface EventDetailRow {
  type: 'event-row';
  groupId: string;
  data: HistoryEventEntry;
  index: number;
}

export interface EventPlaceholderRow {
  type: 'event-placeholder';
  groupId: string;
  index: number;
}

export interface SwapRow {
  type: 'swap-row';
  groupId: string;
  events: HistoryEventEntry[];
  index: number;
  swapKey: string;
}

export interface SwapCollapseRow {
  type: 'swap-collapse';
  groupId: string;
  swapKey: string;
  eventCount: number;
}

export interface MatchedMovementRow {
  type: 'matched-movement-row';
  groupId: string;
  events: HistoryEventEntry[];
  index: number;
  movementKey: string;
}

export interface MatchedMovementCollapseRow {
  type: 'matched-movement-collapse';
  groupId: string;
  movementKey: string;
  eventCount: number;
}

export interface LoadMoreRow {
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

interface UseVirtualRowsReturn {
  flattenedRows: ComputedRef<VirtualRow[]>;
  groupVisibleCounts: Ref<Map<string, number>>;
  expandedSwaps: Ref<Set<string>>;
  expandedMovements: Ref<Set<string>>;
  loadMoreEvents: (groupId: string) => void;
  toggleSwapExpanded: (swapKey: string) => void;
  toggleMovementExpanded: (movementKey: string) => void;
  getRowHeight: (index: number) => number;
  getCardHeight: (index: number) => number;
}

export function useVirtualRows(
  groups: ComputedRef<HistoryEventEntry[]>,
  eventsByGroup: ComputedRef<Record<string, HistoryEventRow[]>>,
): UseVirtualRowsReturn {
  // Track how many items are visible per group (beyond initial limit)
  const groupVisibleCounts = ref<Map<string, number>>(new Map());
  // Track which swap rows are expanded (key: groupId-index)
  const expandedSwaps = ref<Set<string>>(new Set());
  // Track which matched movement rows are expanded (key: groupId-index)
  const expandedMovements = ref<Set<string>>(new Set());

  const flattenedRows = computed<VirtualRow[]>(() => {
    const rows: VirtualRow[] = [];
    const groupsValue = get(groups);
    const eventsMap = get(eventsByGroup);
    const visibleCounts = get(groupVisibleCounts);
    const expandedSwapsSet = get(expandedSwaps);
    const expandedMovementsSet = get(expandedMovements);

    for (const group of groupsValue) {
      const groupId = group.groupIdentifier;

      // 1. Group header (always)
      rows.push({
        type: 'group-header',
        groupId,
        data: group,
      });

      // 2. Events for this group
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
          // Check if this is a matched asset movement (not a swap)
          if (isMatchedMovementGroup(event)) {
            const movementKey = `${groupId}-${i}`;
            const isMovementExpanded = expandedMovementsSet.has(movementKey);

            if (isMovementExpanded) {
              // Add collapse header row
              rows.push({
                type: 'matched-movement-collapse',
                groupId,
                movementKey,
                eventCount: event.length,
              });

              // When expanded, show individual event rows for each event
              event.forEach((subEvent, subIndex) => {
                rows.push({
                  type: 'event-row',
                  groupId,
                  data: subEvent,
                  index: i * 1000 + subIndex, // Unique index for sub-events
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
            // Regular swap
            const swapKey = `${groupId}-${i}`;
            const isSwapExpanded = expandedSwapsSet.has(swapKey);

            if (isSwapExpanded) {
              // Add collapse header row
              rows.push({
                type: 'swap-collapse',
                groupId,
                swapKey,
                eventCount: event.length,
              });

              // When expanded, show individual event rows for each event in the swap
              event.forEach((subEvent, subIndex) => {
                rows.push({
                  type: 'event-row',
                  groupId,
                  data: subEvent,
                  index: i * 1000 + subIndex, // Unique index for sub-events
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
    expandedMovements,
    expandedSwaps,
    flattenedRows,
    getCardHeight,
    getRowHeight,
    groupVisibleCounts,
    loadMoreEvents,
    toggleMovementExpanded,
    toggleSwapExpanded,
  };
}
