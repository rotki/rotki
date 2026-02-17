import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { VirtualRow } from './use-virtual-rows';
import type { HighlightType } from '@/composables/history/events/types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { startPromise } from '@shared/utils';
import { useMediaQuery, useVirtualList, type UseVirtualListReturn } from '@vueuse/core';

const OVERSCAN_COUNT = 15;

interface UseVirtualScrollHighlightOptions {
  flattenedRows: ComputedRef<VirtualRow[]>;
  getRowHeight: (index: number) => number;
  getCardHeight: (index: number) => number;
  highlightedIdentifiers: ComputedRef<string[] | undefined>;
  highlightTypes: ComputedRef<Record<string, HighlightType> | undefined>;
  loading: Ref<boolean>;
  pagination: Ref<TablePaginationData>;
}

interface UseVirtualScrollHighlightReturn {
  containerProps: UseVirtualListReturn<VirtualRow>['containerProps'];
  getHighlightType: (event: HistoryEventEntry) => HighlightType | undefined;
  getSwapHighlightType: (swapEvents: HistoryEventEntry[]) => HighlightType | undefined;
  isCardLayout: Ref<boolean>;
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
    highlightedIdentifiers,
    highlightTypes,
    loading,
    pagination,
  } = options;

  const hasScrolledToHighlight = ref<boolean>(false);
  const pendingHighlightScroll = ref<boolean>(false);

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
   * - If distance <= 3 rows: show both by positioning the earlier one at top.
   * - If distance > 3 rows and secondary is after primary: secondary at bottom of viewport.
   * - If distance > 3 rows and secondary is before primary: secondary at top of viewport.
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
   * Check if an event should be highlighted.
   */
  function isHighlighted(event: HistoryEventEntry): boolean {
    const identifiers = get(highlightedIdentifiers);
    if (!identifiers || identifiers.length === 0)
      return false;
    return identifiers.includes(event.identifier.toString());
  }

  /**
   * Get the highlight type for an event.
   */
  function getHighlightType(event: HistoryEventEntry): HighlightType | undefined {
    const types = get(highlightTypes);
    if (!types)
      return undefined;
    return types[event.identifier.toString()];
  }

  /**
   * Check if any event in a swap/movement group should be highlighted.
   */
  function isSwapHighlighted(swapEvents: HistoryEventEntry[]): boolean {
    const identifiers = get(highlightedIdentifiers);
    if (!identifiers || identifiers.length === 0)
      return false;
    return swapEvents.some(e => identifiers.includes(e.identifier.toString()));
  }

  /**
   * Get the highlight type for a swap/movement group (returns the first matched type).
   */
  function getSwapHighlightType(swapEvents: HistoryEventEntry[]): HighlightType | undefined {
    const types = get(highlightTypes);
    if (!types)
      return undefined;
    for (const event of swapEvents) {
      const type = types[event.identifier.toString()];
      if (type)
        return type;
    }
    return undefined;
  }

  watch(highlightedIdentifiers, () => {
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

  watchDebounced([flattenedRows, highlightedIdentifiers, loading], ([rows, identifiers, isLoading]) => {
    if (isLoading || !identifiers || identifiers.length === 0 || rows.length === 0 || get(hasScrolledToHighlight))
      return;

    const indices = identifiers
      .map(id => ({ id, index: findRowIndexForIdentifier(rows, id) }))
      .filter(item => item.index >= 0);

    if (indices.length === 0)
      return;

    let scrollIndex: number | undefined;

    if (indices.length === 1) {
      const targetIndex = indices[0].index;
      scrollIndex = get(isCardLayout) && targetIndex > 0 ? targetIndex + 2 : targetIndex;
    }
    else if (indices.length === 2) {
      const primaryIndex = indices[0].index;
      const secondaryIndex = indices[1].index;
      scrollIndex = calculateScrollPosition(primaryIndex, secondaryIndex);
    }
    else {
      const lastIndex = indices.at(-1)!.index;
      if (!isRowVisible(lastIndex)) {
        scrollIndex = lastIndex;
      }
    }

    set(hasScrolledToHighlight, true);
    set(pendingHighlightScroll, false);

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
    isHighlighted,
    isSwapHighlighted,
    virtualList,
    wrapperProps,
  };
}
