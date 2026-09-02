import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { VirtualRow } from './use-virtual-rows';
import type { HighlightType } from '@/modules/history/events/action-types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { startPromise } from '@shared/utils';
import { useMediaQuery, useVirtualList, type UseVirtualListReturn } from '@vueuse/core';

const OVERSCAN_COUNT = 15;

interface HighlightScrollTarget {
  /** Whether a highlight target was located; drives whether we mark as scrolled. */
  found: boolean;
  /** Row index to scroll to; `undefined` means "found, but no scroll needed". */
  index?: number;
}

interface UseVirtualScrollHighlightOptions {
  /** The fully flattened row list (group headers, event rows, swap rows) that backs the virtual list; row indices used for scrolling refer to this array. */
  flattenedRows: ComputedRef<VirtualRow[]>;
  /** Height in pixels of the row at the given index in the wide table layout, used when the viewport is above 860px. */
  getRowHeight: (index: number) => number;
  /** Height in pixels of the row at the given index in the narrow card layout, used when the viewport is at most 860px. */
  getCardHeight: (index: number) => number;
  /** Group to highlight as a whole (matched against `groupIdentifier`); used to scroll to its group header when no individual identifiers are given. */
  highlightedGroupIdentifier: MaybeRefOrGetter<string | undefined>;
  /** Individual event identifiers to highlight; the auto-scroll targets these first and only falls back to the group when empty or undefined. */
  highlightedIdentifiers: MaybeRefOrGetter<string[] | undefined>;
  /** Highlight style per target, keyed by event identifier or by `group:<groupIdentifier>`; an entry on the event wins over the group entry. */
  highlightTypes: MaybeRefOrGetter<Record<string, HighlightType> | undefined>;
  /** Whether rows are still being fetched; auto-scroll is suppressed while true so it runs once against final data. */
  loading: Ref<boolean>;
  /** Table pagination state; a page change resets the scroll to the top unless a highlight scroll is pending. */
  pagination: Ref<TablePaginationData>;
}

interface UseVirtualScrollHighlightReturn {
  containerProps: UseVirtualListReturn<VirtualRow>['containerProps'];
  getHighlightType: (event: HistoryEventEntry) => HighlightType | undefined;
  getSwapHighlightType: (swapEvents: HistoryEventEntry[]) => HighlightType | undefined;
  isCardLayout: Ref<boolean>;
  isGroupHighlighted: (groupId: string) => boolean;
  isHighlighted: (event: HistoryEventEntry) => boolean;
  isSwapHighlighted: (swapEvents: HistoryEventEntry[]) => boolean;
  virtualList: UseVirtualListReturn<VirtualRow>['list'];
  wrapperProps: UseVirtualListReturn<VirtualRow>['wrapperProps'];
}

/**
 * Composable for managing virtual scroll highlighting and auto-scroll behavior.
 *
 * Handles:
 * - Virtual list setup with dynamic item heights
 * - Auto-scrolling to highlighted events when data loads
 * - Smart scroll positioning to show multiple highlights when possible
 * - Highlight state helpers for single events and swap/movement groups
 */
export function useVirtualScrollHighlight(options: UseVirtualScrollHighlightOptions): UseVirtualScrollHighlightReturn {
  const {
    flattenedRows,
    getRowHeight,
    getCardHeight,
    highlightedGroupIdentifier,
    highlightedIdentifiers,
    highlightTypes,
    loading,
    pagination,
  } = options;

  const hasScrolledToHighlight = shallowRef<boolean>(false);
  const pendingHighlightScroll = shallowRef<boolean>(false);

  const isCardLayout = useMediaQuery('(max-width: 860px)');

  const getItemHeight = computed<(index: number) => number>(() =>
    get(isCardLayout) ? getCardHeight : getRowHeight,
  );

  const { containerProps, list: virtualList, wrapperProps, scrollTo } = useVirtualList(flattenedRows, {
    itemHeight: (index: number) => get(getItemHeight)(index),
    overscan: OVERSCAN_COUNT,
  });

  /**
   * Find the row index for a given identifier.
   */
  function findRowIndexForIdentifier(rows: VirtualRow[], identifier: string): number {
    return rows.findIndex((row) => {
      if (row.type === 'event-row' || row.type === 'group-header')
        return row.data.identifier.toString() === identifier;
      if (row.type === 'swap-row' || row.type === 'matched-movement-row')
        return row.events.some(e => e.identifier.toString() === identifier);
      return false;
    });
  }

  /**
   * Check if a row index is currently visible in the viewport.
   * Uses the virtualList rendered items, excluding the overscan buffer
   * to approximate actual viewport visibility.
   */
  function isRowVisible(rowIndex: number): boolean {
    const list = get(virtualList);
    if (list.length === 0)
      return false;

    const renderedIndices = list.map(item => item.index);
    const minRendered = Math.min(...renderedIndices);
    const maxRendered = Math.max(...renderedIndices);

    const visibleMin = minRendered + Math.min(OVERSCAN_COUNT, Math.floor(list.length / 4));
    const visibleMax = maxRendered - Math.min(OVERSCAN_COUNT, Math.floor(list.length / 4));

    return rowIndex >= visibleMin && rowIndex <= visibleMax;
  }

  /**
   * Calculate scroll position when both primary and secondary highlights exist.
   *
   * @remarks
   * Within 3 rows, both fit: the earlier one goes to the top. Further apart, only the secondary is
   * placed, at the bottom of the viewport when it follows the primary and at the top when it
   * precedes it.
   */
  function calculateScrollPosition(
    primaryIndex: number,
    secondaryIndex: number,
  ): number {
    const isCard = get(isCardLayout);
    const estimatedViewportRows = isCard ? 3 : 10;
    const distance = Math.abs(secondaryIndex - primaryIndex);

    if (distance <= (isCard ? 1 : 3)) {
      const earlierIndex = Math.min(primaryIndex, secondaryIndex);
      return Math.max(0, earlierIndex);
    }

    if (secondaryIndex > primaryIndex) {
      const bottomOffset = isCard ? 1 : 4;
      return Math.max(0, secondaryIndex - estimatedViewportRows + bottomOffset);
    }
    else {
      return Math.max(0, secondaryIndex);
    }
  }

  /**
   * Check if a group should be highlighted by its group identifier.
   */
  function isGroupHighlighted(groupId: string): boolean {
    return toValue(highlightedGroupIdentifier) === groupId;
  }

  /**
   * Get the highlight type for a group identifier.
   */
  function getGroupHighlightType(groupId: string): HighlightType | undefined {
    const types = toValue(highlightTypes);
    if (!types)
      return undefined;
    return types[`group:${groupId}`];
  }

  /**
   * Check if an event should be highlighted.
   */
  function isHighlighted(event: HistoryEventEntry): boolean {
    const identifiers = toValue(highlightedIdentifiers);
    if (identifiers && identifiers.length > 0 && identifiers.includes(event.identifier.toString()))
      return true;
    return isGroupHighlighted(event.groupIdentifier);
  }

  /**
   * Get the highlight type for an event.
   */
  function getHighlightType(event: HistoryEventEntry): HighlightType | undefined {
    const types = toValue(highlightTypes);
    if (!types)
      return undefined;
    return types[event.identifier.toString()] ?? getGroupHighlightType(event.groupIdentifier);
  }

  /**
   * Check if any event in a swap/movement group should be highlighted.
   */
  function isSwapHighlighted(swapEvents: HistoryEventEntry[]): boolean {
    const identifiers = toValue(highlightedIdentifiers);
    if (identifiers && identifiers.length > 0 && swapEvents.some(e => identifiers.includes(e.identifier.toString())))
      return true;
    return swapEvents.some(e => isGroupHighlighted(e.groupIdentifier));
  }

  /**
   * Get the highlight type for a swap/movement group (returns the first matched type).
   */
  function getSwapHighlightType(swapEvents: HistoryEventEntry[]): HighlightType | undefined {
    const types = toValue(highlightTypes);
    if (!types)
      return undefined;
    for (const event of swapEvents) {
      const type = types[event.identifier.toString()];
      if (type)
        return type;
    }
    for (const event of swapEvents) {
      const type = getGroupHighlightType(event.groupIdentifier);
      if (type)
        return type;
    }
    return undefined;
  }

  watch([(): string[] | undefined => toValue(highlightedIdentifiers), (): string | undefined => toValue(highlightedGroupIdentifier)], () => {
    set(hasScrolledToHighlight, false);
    set(pendingHighlightScroll, true);
  });

  watch(pagination, (current, previous) => {
    if (!previous)
      return;

    if (current.page !== previous.page && !get(pendingHighlightScroll)) {
      scrollTo(0);
    }
  });

  /**
   * Locate the group-header row for a whole-group highlight (used when no
   * individual identifiers are given).
   */
  function resolveGroupScroll(rows: VirtualRow[], groupId: string | undefined): HighlightScrollTarget {
    if (!groupId)
      return { found: false };

    const groupIndex = rows.findIndex(row => row.type === 'group-header' && row.groupId === groupId);
    if (groupIndex < 0)
      return { found: false };

    return { found: true, index: groupIndex };
  }

  /**
   * Locate the scroll target for individual identifier highlights, positioning
   * to show as many as possible: a single target directly, two via
   * calculateScrollPosition, and three or more only when the last is offscreen.
   */
  function resolveIdentifierScroll(rows: VirtualRow[], identifiers: string[] | undefined): HighlightScrollTarget {
    if (!identifiers || identifiers.length === 0)
      return { found: false };

    const indices = identifiers
      .map(id => ({ id, index: findRowIndexForIdentifier(rows, id) }))
      .filter(item => item.index >= 0);

    if (indices.length === 0)
      return { found: false };

    if (indices.length === 1) {
      const targetIndex = indices[0].index;
      return { found: true, index: get(isCardLayout) && targetIndex > 0 ? targetIndex + 2 : targetIndex };
    }

    if (indices.length === 2)
      return { found: true, index: calculateScrollPosition(indices[0].index, indices[1].index) };

    const lastIndex = indices.at(-1)!.index;
    return { found: true, index: isRowVisible(lastIndex) ? undefined : lastIndex };
  }

  watchDebounced([flattenedRows, (): string[] | undefined => toValue(highlightedIdentifiers), (): string | undefined => toValue(highlightedGroupIdentifier), loading], ([rows, identifiers, groupId, isLoading]) => {
    if (isLoading || rows.length === 0 || get(hasScrolledToHighlight))
      return;

    const hasIdentifiers = !!identifiers && identifiers.length > 0;
    if (!hasIdentifiers && !groupId)
      return;

    const target = hasIdentifiers
      ? resolveIdentifierScroll(rows, identifiers)
      : resolveGroupScroll(rows, groupId);

    if (!target.found)
      return;

    set(hasScrolledToHighlight, true);
    set(pendingHighlightScroll, false);

    const scrollIndex = target.index;
    if (scrollIndex !== undefined) {
      startPromise(nextTick(() => {
        scrollTo(scrollIndex);
      }));
    }
  }, { debounce: 200 });

  return {
    containerProps,
    getHighlightType,
    getSwapHighlightType,
    isCardLayout,
    isGroupHighlighted,
    isHighlighted,
    isSwapHighlighted,
    virtualList,
    wrapperProps,
  };
}
